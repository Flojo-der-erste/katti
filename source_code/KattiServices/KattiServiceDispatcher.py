import copy
import datetime
import logging
import multiprocessing
import os
import signal
import sys
import threading
import traceback
from dataclasses import field, dataclass
import psutil
import time
from multiprocessing import Process
from KattiLogging.KattiLogging import setup_logger
from DataBaseStuff.ConnectDisconnect import connect_to_database, disconnect_to_database
from KattiServices.KattiDispatcherDocument import KattiServiceDB, KattiDispatcherDB, KillCandidate
from KattiServices.BaseKattiSerivce import KattiServiceConfig
from KattiServices.ServiceClassMapping import service_class_mapping


@dataclass
class DispatcherConfig:
    log_level: int = field(default=logging.DEBUG)
    db_cfg: MongoDB = MongoDB.get_config()
    name: str = field(default='test')
    max_dispatched_processes: int = field(default=30)


@dataclass
class DispatchedService:
    python_process: Process
    service_cfg: KattiServiceConfig

    def get_status_id(self):
        return self.service_cfg.status_id


class KattiServiceManager:
    def __init__(self, logger, raw_service_cfg: KattiServiceConfig):
        self.logger = logger
        self.katti_services: dict = {}
        self.raw_service_cfg: KattiServiceConfig = raw_service_cfg

    @property
    def services_count(self):
        return len(self.katti_services)

    def delete_all_services(self):
        for service in self.katti_services:
            KattiServiceDB.set_is_alive(service.get_status_id(), False)
        self.katti_services = {}

    def check_service_processes(self):
        x = {} # TODO other solution
        for service_id, dispatched_service in self.katti_services.items():
            if not dispatched_service.python_process.is_alive():
                self.logger.debug(f'Process {dispatched_service.python_process} ist not alive, delete it')
                try:
                    dispatched_service.python_process.join()
                except Exception:
                    pass
                KattiServiceDB.set_is_alive(dispatched_service.get_status_id(), False)
            else:
                x.update({service_id: dispatched_service})
        self.katti_services = x

    def kill_killing_candidates(self, candidates: list[KillCandidate], wait_time_for_suizide):
        x = []
        for candidate in candidates:
            service = self.katti_services[candidate.service_id]
            match candidate.status:
                case 'not started':
                    self.logger.debug(f'Set stop signal {candidate.service_id}')
                    service.service_cfg.stop_event.set()
                    candidate.start_killing = datetime.datetime.utcnow()
                    candidate.status = 'wait for dead'
                    x.append(candidate)
                case 'wait for dead':
                    if not (datetime.datetime.utcnow() - candidate.start_killing).seconds < wait_time_for_suizide:
                        self.logger.debug(f'I have to kill {candidate.service_id}')
                        try:
                            service.kill()
                        except Exception:
                            self.logger.error(traceback.format_exception(*sys.exc_info()))
                case _:
                    x.append(candidate)
        return x

    def add_and_start_new_process(self, raw_service: KattiServiceDB):
        self.logger.debug(f'Start new service with id {raw_service["_id"]}. Service cls: {raw_service["_cls"]}')
        try:
            service_cls = service_class_mapping[raw_service["_cls"]]
        except Exception:
            self.logger.error(traceback.format_exception(*sys.exc_info()))
        else:
            help = copy.deepcopy(self.raw_service_cfg)
            help.status_id = raw_service['_id']
            help.stop_event = multiprocessing.Event()
            new_service = DispatchedService(python_process=service_cls(help),
                                            service_cfg=help)
            self.katti_services.update({new_service.service_cfg.status_id: new_service})
            new_service.python_process.start()
            KattiServiceDB.set_is_alive(raw_service['_id'], True)
    def shutdown_protocol(self):
        self.logger.debug('Set stop event for services')
        for service_id, dispatched_service in  self.katti_services.items():
            dispatched_service.service_cfg.stop_event.set()


class KattiServiceDispatcher:
    def __init__(self, configuration: DispatcherConfig, stop_event: threading.Event):
        super().__init__()
        self._configuration = configuration
        self._logger = None
        self._stop: threading.Event = stop_event
        self._my_status: KattiDispatcherDB | None = None

    def do_it(self):
        connect_to_database()
        self._my_status = KattiDispatcherDB.register_at_system(node_name=self._configuration.name)
        self._logger = setup_logger(name=f'Dispatcher-{self._configuration.name}<:>{self._my_status.id}', level=self._configuration.log_level)
        self._process_managment: KattiServiceManager = KattiServiceManager(self._logger.getChild('process_management'), raw_service_cfg=KattiServiceConfig(log_Level=self._logger.level, db=self._configuration.db_cfg))
        self._logger.debug('Start')
        self._setup_signal_handling()
        self._start_dispatching()
        self._shutdown_protocol()
        self._logger.info('This is my last message: I love you Katti <3')

    def _shutdown_protocol(self, x=None, y=None):
        self._logger.info('Start shutdown protocol')
        self._my_status.set_stattus('shutdown protocol')
        self._process_managment.shutdown_protocol()
        self._logger.info(f'Start waiting for services. Wait time is {self._my_status.shutdown_wait_time_s}')
        self._wait_for_services()
        self._logger.info('Start suicide protocol')
        self._suicide()
        self._my_status.set_stattus('stop')
        disconnect_to_database()

    def _wait_for_services(self):
        start_time = datetime.datetime.now()
        while self._process_managment.services_count > 0 and (datetime.datetime.now() - start_time).seconds <= self._my_status.shutdown_wait_time_s:
            self._process_managment.check_service_processes()
            self._my_status.set_heartbeat()
            time.sleep(self._my_status.wait_time_in_loop_s)

    def _start_dispatching(self):
        self._logger.info('Start dispatching')
        while not self._stop.is_set() and not self._my_status.should_i_stop:
            try:
                self._my_status.reload()
                self._my_status.set_heartbeat()
                self._my_status.kill_candidates = self._process_managment.kill_killing_candidates(self._my_status.kill_candidates, self._my_status.shutdown_wait_time_s)
                self._process_managment.check_service_processes()
                #TODO: restart porocesses
                self._get_undisptached_services()
                self._build_status_update()
            except KeyboardInterrupt:
                break
            except Exception:
                self._logger.error(traceback.format_exception(*sys.exc_info()))
            time.sleep(self._my_status.wait_time_in_loop_s)
        self._logger.info(f'Stop dispatching. Stop_event {self._stop.is_set()}, status stop flag {self._my_status.should_i_stop}')

    def _get_undisptached_services(self):
        while self._process_managment.services_count < self._my_status.max_dispatched_processes:
            new_service = self._get_services_for_restart()
            if not new_service:
                new_service = self._get_service_for_first_start()
            if not new_service:
                break
            else:
                self._logger.debug(f'New Service, id {new_service["_id"]}')
                self._process_managment.add_and_start_new_process(new_service)

    def _get_services_for_restart(self):
        return KattiDispatcherDB.get_service_for_first_start(self._my_status.id, self._my_status.with_crawling_services)

    def _get_service_for_first_start(self):
       return KattiDispatcherDB.get_service_for_restart(self._my_status.id, self._my_status.with_crawling_services)

    def _build_status_update(self):
        self._my_status.services_counter = self._process_managment.services_count
        self._my_status.save()

    def _kill_my_children(self):
        self._logger.info('Start killing my children')
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        self._logger.debug(children)
        for child in children:
            try:
                self._logger.debug(f'Child pid: {child.pid} goodbye! name: {child.name()}')
                os.kill(child.pid, signal.SIGKILL)
            except Exception:
                excp = traceback.format_exception(*sys.exc_info())
                self._logger.exception(f'Can"t kill-child process \n{excp}')
                print(excp)

    def _suicide(self):
        self._logger.debug(f'I will die...')
        try:
            self._kill_my_children()
        finally:
            self._logger.debug(f'Finally... Goodbye')
            self._process_managment.delete_all_services()
            try:
                os.kill(multiprocessing.current_process().pid, signal.SIGKILL)
            except Exception:
                excp = traceback.format_exception(*sys.exc_info())
                self._logger.exception(f'Can"t kill process \n{excp}')

    def _setup_signal_handling(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, self._shutdown_protocol)

