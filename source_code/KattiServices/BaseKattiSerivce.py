import datetime
import logging
import multiprocessing
import os
import signal
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from multiprocessing import Process
import psutil
from KattiLogging.KattiLogging import setup_logger
from bson import ObjectId
from DataBaseStuff.ConnectDisconnect import connect_to_database, disconnect_to_database
from KattiServices.KattiDispatcherDocument import KattiServiceDB

from Utils.KillTimer import KillTimer

class ToMuchStarts(Exception):
    pass

@dataclass
class KattiServiceConfig:
    log_Level: int = field()
    stop_event: threading.Event | None = None
    status_id: ObjectId | None = None


class BaseKattiService(Process):

    def __init__(self, config: KattiServiceConfig):
        super().__init__()
        self._katti_config: KattiServiceConfig  = config
        self.logger: logging.Logger | None = None
        self.db_document: KattiServiceDB | None = None
        self._i_am_finished: bool = False
        self._init()
        self._kill_timer = None
        self.sleep_time = 0

    @property
    def my_name(self) -> str:
        return f'CrawlingService_{self._katti_config.status_id}'

    @property
    def is_stop(self) -> bool:
        if self.db_document.action == 'break' or self._katti_config.stop_event.is_set():
            self._i_am_finished = True
            return True
        return False

    @property
    def db_document_cls(self):
        raise NotImplementedError

    def _next_control_round(self):
        raise NotImplementedError

    def _shutdown(self):
        raise NotImplementedError

    def _init(self):
        raise NotImplementedError

    def _prepare_service(self):
        raise NotImplementedError

    def run(self):
        connect_to_database()
        self._katti_config.stop_event = multiprocessing.Event() #TODOD ändere da
        self.db_document = self.db_document_cls.objects.get(id=self._katti_config.status_id)
        self.db_document.process_pid = f'{self.pid}'

        self.logger = setup_logger(name=self.my_name,
                                   level=self._katti_config.log_Level)
        self.logger.info(f'Service ist started and running, id: {self.db_document.id}')
        self.db_document.set_status('running')
        try:
            self._check_start_counter()
            self.logger.info('Prepare Service')
            self._prepare_service()
            self.logger.info('Start service work')
            while not self.is_stop and not self._i_am_finished:
                self.sleep_time = 0
                self.db_document.set_heartbeat_update_and_sync(new_update='Start next round.')
                self._next_control_round()
                self._sleep()
        except ToMuchStarts:
            self.logger.exception(f'To much starts. Counter: {self.db_document.start_counter}, Max: {self.db_document.max_starts}')
        except Exception:
            self.logger.exception(traceback.format_exception(*sys.exc_info()))
        finally:
            self.logger.info(f'Start shutdown: Is stop {self.is_stop}, finished {self._i_am_finished}')
            self.db_document.set_status('break')
            self._suicide()
            self.logger.debug('Disconnect DB')
            disconnect_to_database()

    def _sleep(self):
        start = datetime.datetime.utcnow()
        self.db_document.set_heartbeat_update_and_sync(new_update=f'Start sleep {self.db_document.sleep_time}  {self.sleep_time}')
        while (self.sleep_time > 0 and (datetime.datetime.utcnow() - start).seconds < self.sleep_time) or (datetime.datetime.utcnow() - start).seconds < self.db_document.sleep_time:
            if self.is_stop:
                break
            self.db_document.set_heartbeat_update_and_sync(new_update='Sleeping')
            time.sleep(1)

    def _check_start_counter(self):
        self.db_document.rebuild_counter += 1
        if not self.db_document.max_rebuilds == 0 and self.db_document.rebuild_counter > self.db_document.max_rebuilds:
            raise ToMuchStarts()
    def _sync_with_db(self):
        self.db_document.set_heartbeat_update_and_sync(new_update='End round.')
        self.db_document.reload()

    def _setup_signal_handling(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, self._suicide)

    def reset_timer(self):
        if not self._kill_timer:
            self._kill_timer = KillTimer(timeout_func=self._suicide, logger=self.logger.getChild('KillTimer'))
        self._kill_timer.stop()
        self._kill_timer.start(self.db_document.kill_timer.time_before_kill_seconds)
    def _kill_my_children(self):
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        self.logger.debug(children)
        for child in children:
            try:
                self.logger.debug(f'Child pid: {child.pid} goodbye! name: {child.name()}')
                os.kill(child.pid, signal.SIGKILL)
            except Exception:
                self.logger.exception(f'Can"t kill-child process \n{traceback.format_exception(*sys.exc_info())}')

    def _suicide(self, x=None, y=None):  # x und y wegen aufruf der Funktion im Timer.
        self.logger.debug(f'I will die...')
        try:
            self._shutdown()
        finally:
            self.logger.debug(f'Finally... Goodbye. Start killing my children')
            self._kill_my_children()
            try:
                if self.db_document.restart and not self._i_am_finished:
                    self.db_document.modify(set__action='restart', push__suicide_times=datetime.datetime.utcnow())
                else:
                    self.db_document.modify(push__suicide_times=datetime.datetime.utcnow())
            except Exception:
                self.logger.exception(traceback.format_exception(*sys.exc_info()))
            try:
                os.kill(multiprocessing.current_process().pid, signal.SIGKILL)
            except Exception:
                self.logger.exception(traceback.format_exception(*sys.exc_info()))


