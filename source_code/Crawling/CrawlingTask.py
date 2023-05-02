import datetime
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from celery import Task
from DataBaseStuff.ConnectDisconnect import get_database_configs
from bson import ObjectId
from Crawling.DockerCommunicatorServer import DockerCommunicatorServer, CrawlingCMD, WindowStatsCMD, \
    SaveDataToDBCMD, StartWebdriverCMD, DownloadFinishedCMD, PingCMD, Reset, \
    SaveBrowserProfileToDB
import docker
from Crawling.Exceptions import NoDockerAnswer, WebdriverDidNotStarted, WindowStatsSucks, FrozenBaby, UnknownError, \
    SaveDataToDB, CrawlingDidNotStarted, SaveProfileToDB, NameorServiceNotKnownException, StatusCodeException, \
    ToMuchDockerRestarts, ResetException
from Crawling.WorkFlowFunctions import Ad_Workflow, Anti_Bot
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle, CeleryCrawlingOpData, SubTiming
from DataBaseStuff.MongoengineDocuments.Crawling.SpiderTrack import SpiderConfig
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from Utils.ConfigurationClass import Docker

TEST = False

class CrawlingRetry(Exception):
    pass

def set_update_status(func):
    def do_update(*args, **kwargs):
        args[0]._task.update_state(state='PROGRESS', meta={'step': func.__name__.replace('_', ''),
                                                           'bundle': str(args[0].next_bundle.id)})
        return func(*args, **kwargs)

    return do_update


@dataclass
class CrawlingTaskData:
    browser_config_id: ObjectId
    crawling_config_id: ObjectId
    request_id: ObjectId
    group_id: str
    random: bool = True
    statefull: bool = False
    bundle_ids: list[ObjectId] = field(default_factory=list)
    spider_mode: SpiderConfig | None = None
    with_analysis: bool = True

    @property
    def next_bundle_id(self) -> ObjectId | None:
        if len(self.bundle_ids) == 0:
            return None
        else:
            return self.bundle_ids.pop()


class CrawlingTask:
    def __init__(self, logger, task: Task, crawling_data: CrawlingTaskData):
        global TEST
        self._logger = logger
        self._docker_container = None
        if TEST:
            self._channel_id = '5'
        else:
            self._channel_id = f'{uuid.uuid4()}'
        self._docker_communicator = DockerCommunicatorServer(channel_id=self._channel_id)
        self.crawling_data: CrawlingTaskData = crawling_data
        self._task = task
        self._error_code = 0
        self.next_bundle: Bundle | None = None
        self.first_run = True

        self._docker_cfg: Docker = Docker.get_config()

        self._redis_mongo_cache = RedisMongoCache()
        self._crawling_config: CrawlingConfig = self._redis_mongo_cache.get_mongoengine_cache(
            cache_key=f'{self.crawling_data.crawling_config_id}', mongoengine_cls=CrawlingConfig,
            mongo_filter={'id': self.crawling_data.crawling_config_id})
        self._browser_config: BrowserConfig.Config = self._redis_mongo_cache.get_mongoengine_cache(
           cache_key=f'{self.crawling_data.browser_config_id}', mongoengine_cls=BrowserConfig,
            mongo_filter={'id': self.crawling_data.browser_config_id}).config
        self.docker_webdriver_start_timings: list[SubTiming] = []

        self._after_crawl_funcs = []

        if self._browser_config.workflow == 'with_iframe_fun_standalone':
            self._after_crawl_funcs.append(Ad_Workflow())
        if self._browser_config.simulating_user_actions:
            self._after_crawl_funcs.append(Anti_Bot())

    @property
    def _docker_id(self):
        global TEST
        if TEST:
            return 'test_run'
        return self._docker_container.id

    def init_bundle(self, bundle_id: ObjectId, crawling_op_status: CeleryCrawlingOpData):
        self.next_bundle = self._redis_mongo_cache.get_mongoengine_cache(cache_key=f'{bundle_id}',
                                                                         mongoengine_cls=Bundle,
                                                                         mongo_filter={'id': bundle_id})
        self._crawling_op_status = crawling_op_status
        self.next_bundle.update_celery_task_status(self._crawling_op_status)

    def execute_request(self):
        try:
            self._start_crawling_process()
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            raise
        finally:
            self.next_bundle.update_celery_task_status(self._crawling_op_status)

    def start_protocol(self):
        if self._crawling_op_status.docker_restart_counter >= self._crawling_config.docker_max_docker_restarts:
            raise ToMuchDockerRestarts()
        self._crawling_op_status.docker_restart_counter += 1
        try:
            self._start_docker()
            self._docker_communicator.reset_channel()
            self._docker_communicator.send_command(PingCMD(),
                                                   wait_time_for_execution=self._crawling_config.docker_wait_ping_pong)
            self._logger.debug(f'Docker_id {self._docker_id}')
            self._start_webdriver()
        except (NoDockerAnswer, WebdriverDidNotStarted):
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            self.next_bundle.update_celery_task_status(self._crawling_op_status)
            self.shutdown_protocol()
            self.start_protocol()

    def shutdown_protocol(self):
        if self._docker_container:
            self._logger.debug(f'Kill docker {self._docker_container.id}')
            try:
                if self._docker_container:
                    self._docker_container.kill()
                    self._docker_container = None
            except Exception:
                self._logger.exception(traceback.format_exception(*sys.exc_info()))

    def _start_docker(self):
        global TEST
        self._logger.debug('Start docker container')
        if not TEST:
            start = datetime.datetime.utcnow()
            cfg = get_database_configs()
            self._crawling_op_status.docker_container_name = f'{self.next_bundle.id}_{uuid.uuid4()}'
            client = docker.DockerClient(self._docker_cfg.docker_host)
            self._docker_container = client.containers.run(self._docker_cfg.crawler_docker_container_name,
                                                           remove=True,
                                                           detach=True,
                                                           name=self._crawling_op_status.docker_container_name,
                                                           command=f'--ch_id {self._channel_id} --task_id {self._task.request.id} --mongo_uri {cfg.get_mongodb_uri_for_user()} --redis_host {cfg.redis.host} --redis_port {cfg.redis.port} --redis_pw {cfg.redis.password} --log_name {self._task.request.id}_logger',
                                                           **self._docker_cfg.extra_args)
            self._playing_ping_pong_with_docker()
            end = datetime.datetime.utcnow()
            self.docker_webdriver_start_timings.append(
                SubTiming(description='Docker start',start_execution=start,stop_execution=end, time=(end - start).total_seconds()))

    def _playing_ping_pong_with_docker(self):
        self._logger.debug('Start playing ping pong with docker')
        self._docker_communicator.play_ping_pong(self._crawling_config.wait_time_for_docker_ready)

    def _start_webdriver(self):
        self._logger.debug('Start webdriver')
        cmd = StartWebdriverCMD(display_colour_depth=24, browser_config_id=self.crawling_data.browser_config_id,
                                common_crawling_config_id=self.crawling_data.crawling_config_id)
        answer = self._send_command_to_docker(cmd=cmd, wait_time=self._crawling_config.docker_wait_for_new_webdriver,
                                              exception_cls=WebdriverDidNotStarted)
        if answer.timing:
            self.docker_webdriver_start_timings.append(answer.timing)

    def _start_crawling_process(self):
        self._logger.debug(f'Start with crawling process {self.next_bundle}')
        try:
            self._send_command_to_docker(cmd=Reset(),
                                         wait_time=self._crawling_config.docker_wait_time_reset,
                                         exception_cls=ResetException)
            self._crawling_op_status.url_retry_counter += 1
            self._start_crawl_url(self.next_bundle)
            self._wait_after_loading()
            self._send_command_to_docker(cmd=WindowStatsCMD(action_id='after_loading'),
                                         wait_time=self._crawling_config.docker_wait_window_stats_execution,
                                         exception_cls=WindowStatsSucks)
            for workflow in self._after_crawl_funcs:
                workflow.workflow(communicator=self._docker_communicator,
                                  browser_config=self._browser_config,
                                  crawling_config=self._crawling_config)
            self._wait_for_downloads()
            self._save_data_to_db()
        except (StatusCodeException, WindowStatsSucks, SaveDataToDB, SaveProfileToDB) as e:
            self._logger.error(f'{e}')
            self._crawling_op_status.exceptions.append(f'{e}')
            if not self.crawling_data.statefull:
                self._restart_docker()
        except(NoDockerAnswer, CrawlingDidNotStarted, UnknownError, FrozenBaby) as e:
            self._logger.error(f'{e}')
            self._crawling_op_status.exceptions.append(f'{e}')
            if self.crawling_data.statefull:
                raise CrawlingRetry()
            self._restart_docker()
        except NameorServiceNotKnownException as e:
            self._crawling_op_status.exceptions.append(f'{e}')
            self._logger.debug(f'URL not known {self.next_bundle.crawling_url}')

    @set_update_status
    def _save_data_to_db(self):
        self._send_command_to_docker(cmd=SaveDataToDBCMD(), wait_time=self._crawling_config.docker_wait_for_save_data,
                                     exception_cls=SaveDataToDB)
        self._send_command_to_docker(cmd=SaveBrowserProfileToDB(),
                                     wait_time=self._crawling_config.docker_wait_for_save_data,
                                     exception_cls=SaveProfileToDB)

    @set_update_status
    def _wait_for_downloads(self):
        start_time = datetime.datetime.utcnow()
        while (datetime.datetime.utcnow() - start_time).total_seconds() < self._browser_config.max_download_wait_time_s:
            answer = self._docker_communicator.send_command(cmd=DownloadFinishedCMD(), wait_time_for_execution=self._crawling_config.docker_common_wait_time_for_answer)
            if answer.all_finished:
                self._logger.debug('All downloads finished or no downloads :)')
                return
            else:
                self._logger.debug('Not all downloads are finished')
                time.sleep(0.3)
        self._crawling_op_status.download_wait_time_to_short = True

    @set_update_status
    def _wait_after_loading(self):
        time.sleep(self._browser_config.wait_after_crawl)


    def _restart_docker(self):
        self.shutdown_protocol()
        self.start_protocol()
        self._logger.debug('Docker is ready')
        self._crawling_op_status.docker_restart_counter += 1
        self._start_crawling_process()

    @set_update_status
    def _start_crawl_url(self, url):
        self._logger.debug(f'Crawl url {self.next_bundle.crawling_url.url}')
        self._send_command_to_docker(cmd=CrawlingCMD(bundle_id=self.next_bundle.id,
                                                     crawling_url=self.next_bundle.crawling_url.url),
                                     wait_time=self._browser_config.page_load_timeout + 20,
                                     exception_cls=FrozenBaby)

    def _send_command_to_docker(self, cmd, wait_time, exception_cls):
        try:
            answer = self._docker_communicator.send_command(cmd=cmd, wait_time_for_execution=wait_time)
        except NoDockerAnswer:
            raise exception_cls('No docker answer.')
        else:
            match answer.error_code:
                case 0:
                    return answer
                case 4203:
                    raise NameorServiceNotKnownException()
                case 4204:
                    raise StatusCodeException('Bad status code')
                case 4205 | -1 | 4207:
                    raise UnknownError()
                case 4206:
                    raise Exception('Unknown browser wrapper')
                case _:
                    raise Exception(f'{answer}')
