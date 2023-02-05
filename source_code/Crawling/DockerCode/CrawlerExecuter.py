import datetime
import functools
import io
import os
import sys
import time
import traceback
import typing
import uuid
import zipfile
from io import BytesIO
from tarfile import TarFile
from selenium.webdriver.common.by import By
from Crawling.DockerCode.DockerKonstanten import PLUGIN_DIR, INIT_PROFILE_DIR
from Crawling.Exceptions import NoCommandException, NameOrServiceNotKnownException, StatusCodeException
from pyvirtualdisplay import Display
from selenium.common.exceptions import TimeoutException
from Crawling.BrowserWrappers.BaseWebDriverWrapper import WebDriverWrapper, URL_LOCK, HEADERS_ALL, REGEX_HEADERS
from Crawling.BrowserWrappers.FirefoxWrapper import FirefoxWrapper
from Crawling.BrowserWrappers.MicrosoftEdgeChromeChromiumWrapper import ChromeWrapper, EdgeWrapper, UndetectedChrome, \
    ChromiumWrapper
from Crawling.Utils.FakeUserInteraction import fake_user_interaction
from DataBaseStuff.GridFsStuff import gridfs_get_data
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.BrowserAndExtension import BrowserExtension
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import SubTiming
from Crawling.DockerCode.DataToDB import DataToDB
from Crawling.DockerCode.PluginMobilePhone import PluginLogReceiver
from Crawling.DockerCode.iFramesAreStupid import IFramesAreStupid2
from Crawling.DockerCommunicatorServer import DockerCommunicatorClient, StartWebdriverCMD, \
    DockerCMD, IFrameFun, WindowStatsCMD, CrawlingCMD, SaveDataToDBCMD, FakeUserInteraction, DownloadFinishedCMD, \
    PingCMD, DockerAnswer, DockerAnswerCrawling, DockerAnswerDownloads, PongAnswer, Reset, SaveBrowserProfileToDB, \
    WebdriverStartAnswer
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.ChromiumBasedOptions import EdgeOptions, \
    ChromiumOptions, ChromeUndectOptions, ChromeOptions
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.FirefoxOptions import FirefoxOptions
from RedisCacheLayer.RedisMongoCache import RedisMongoCache, ManualConnectionSettings
from seleniumwire import webdriver


class Timings:
    def __init__(self):
        self.timings: list[SubTiming] = []
        self._timing_objc: SubTiming | None = None

    def reset(self):
        self.timings = []
        self._timing_objc = None

    def start(self, description: str):
        self._timing_objc = SubTiming(description=description, start_execution=datetime.datetime.utcnow())

    def stop(self):
        if self._timing_objc:
            self._timing_objc.stop_execution = datetime.datetime.utcnow()
            self._timing_objc.time = (self._timing_objc.stop_execution - self._timing_objc.start_execution).total_seconds()
            self.timings.append(self._timing_objc)


TIMINGS_WATCH: Timings = None
EXTRA_DATA_FOR_DB = {}


def logging_and_timing(logging=True, timing=True):
    def first(func):
        @functools.wraps(func)
        def do_it(*args, **kwargs):
            global TIMINGS_WATCH
            if logging:
                args[0]._logger.debug(f'{func.__name__.replace("_", "")}')
            if timing:
                TIMINGS_WATCH.start(func.__name__)
                return_value = func(*args, **kwargs)
                TIMINGS_WATCH.stop()
                return return_value
            return func(*args, **kwargs)
        return do_it
    return first


class CrawlerExecuter:
    def __init__(self, logger, redis_con_data: ManualConnectionSettings, channel_id: str):
        global TIMINGS_WATCH
        self._logger = logger
        self._browser_wrapper: WebDriverWrapper | None = None

        self._display = None
        self._plugin_mobile_phone: PluginLogReceiver = PluginLogReceiver()
        self._plugin_mobile_phone.start()
        self._redis_mongo_cache: RedisMongoCache = RedisMongoCache(manual_con_data=redis_con_data)
        self._communicator_client: DockerCommunicatorClient = DockerCommunicatorClient(channel_id=channel_id,
                                                                                       redis_con=self._redis_mongo_cache.redis_connection)

        self._common_crawling_config: CrawlingConfig | None = None
        self._browser_config: BrowserConfig.Config | None = None
        self._next_crawling_cmd: CrawlingCMD | None = None
        TIMINGS_WATCH = Timings()
        self._data_to_db: DataToDB | None = None
        self._webdriver_start_timing: SubTiming | None = None

    @property
    def selenium_webdriver(self) -> webdriver:
        return self._browser_wrapper.driver

    def run(self):
        while True:
            try:
                next_cmd = self._communicator_client.get_next_command()
            except NoCommandException:
                time.sleep(0.1)
                continue
            else:
                self._new_command(next_cmd)

        self._plugin_mobile_phone.stop()
        self._shutdown_webbrowser()
        self._logger.info('Finished.')

    def _new_command(self, new_command: typing.Union[DockerCMD]):
        self._docker_answer = None
        try:
            if isinstance(new_command, PingCMD):
                self._docker_answer = PongAnswer(error_code=0)

            elif isinstance(new_command, StartWebdriverCMD):
                self._execute_start_webdriver_cmd(new_command)

            elif isinstance(new_command, IFrameFun):
                self._execute_iframe_fun_cmd(new_command)

            elif isinstance(new_command, WindowStatsCMD):
                self._execute_window_stats_cmd(new_command)

            elif isinstance(new_command, CrawlingCMD):
                self._execute_crawling_cmd(new_command)

            elif isinstance(new_command, SaveDataToDBCMD):
                self._execute_save_data_to_db_cmd(new_command)

            elif isinstance(new_command, FakeUserInteraction):
                self._fake_user_interaction()

            elif isinstance(new_command, SaveBrowserProfileToDB):
                self._execute_save_browser_profile(new_command)

            elif isinstance(new_command, DownloadFinishedCMD):
                self._execute_download_finished_cmd(new_command)

            elif isinstance(new_command, Reset):
                self._logger.debug(f'Reset')
                global WINDOW_STATS, ROOT_IFRAMES, CHILD_IFRAMES, TIMINGS_WATCH, EXTRA_DATA_FOR_DB
                self._plugin_mobile_phone.reset()
                TIMINGS_WATCH.reset()
                WINDOW_STATS, ROOT_IFRAMES, CHILD_IFRAMES = [], [], []
                EXTRA_DATA_FOR_DB = {}
                self._docker_answer = PongAnswer(error_code=0)

        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            self._docker_answer = DockerAnswer(error_code=600)

        finally:
            self._communicator_client.send_response(self._docker_answer)

    @logging_and_timing()
    def _execute_save_browser_profile(self, cmd):
        self._init_save_to_db()
        self._data_to_db.save_browser_profile(path=self._browser_wrapper._src_browser_profile_path, profile_to_redis=cmd.save_backup_profile_to_redis)
        self._docker_answer = DockerAnswer(error_code=0)

    @logging_and_timing(timing=False)
    def _execute_save_data_to_db_cmd(self, save_data_cmd: SaveDataToDBCMD):
        global WINDOW_STATS, TIMINGS_WATCH, EXTRA_DATA_FOR_DB
        self._init_save_to_db()
        self._data_to_db.saving_it(
            seleniumwire_requests=self.selenium_webdriver.requests,
            browser_logs=self._plugin_mobile_phone.get_browser_logs(),
            window_stats=WINDOW_STATS,
            sub_timings=TIMINGS_WATCH.timings,
            bundle_id=self._next_crawling_cmd.bundle_id,
            extra_data=EXTRA_DATA_FOR_DB)
        self._docker_answer = DockerAnswer(error_code=0)

    def _init_save_to_db(self):
        if not self._data_to_db:
            self._data_to_db = DataToDB(logger=self._logger)

    @logging_and_timing()
    def _execute_download_finished_cmd(self, download_finished_cdm: DownloadFinishedCMD):
        answer = self._plugin_mobile_phone.all_downloads_finished()
        self._docker_answer = DockerAnswerDownloads(error_code=0, all_finished=answer)

    @logging_and_timing()
    def _fake_user_interaction(self):
        fake_user_interaction(self.selenium_webdriver)
        self._docker_answer = DockerAnswer(error_code=0)

    @logging_and_timing()
    def _execute_start_webdriver_cmd(self, start_webdriver_cmd: StartWebdriverCMD):
        time_start = datetime.datetime.utcnow()
        self._common_crawling_config: CrawlingConfig = self._redis_mongo_cache.get_mongoengine_cache(
            cache_key=f'{start_webdriver_cmd.common_crawling_config_id}', mongoengine_cls=CrawlingConfig,
            mongo_filter={'id': start_webdriver_cmd.common_crawling_config_id})
        self._browser_config: BrowserConfig.Config = self._redis_mongo_cache.get_mongoengine_cache(
            cache_key=f'{start_webdriver_cmd.browser_config_id}', mongoengine_cls=BrowserConfig,
            mongo_filter={'id': start_webdriver_cmd.browser_config_id}).config
        if not self._download_extensions() and not start_webdriver_cmd.ignore_extension_download_error:
            self._docker_answer = DockerAnswer(error_code=4201)
            return
        if start_webdriver_cmd.backup_profile_id and not self._download_backup_profile(start_webdriver_cmd) and not start_webdriver_cmd.ignore_profile_db_error:
            self._docker_answer = DockerAnswer(error_code=4202)
            return
        self._display = Display(size=(self._browser_config.window_size_x,
                                      self._browser_config.window_size_y),
                                color_depth=start_webdriver_cmd.display_colour_depth, visible=False)
        self._display.start()
        self._docker_answer = self._start_browser_wrapper(start_webdriver_cmd.backup_profile_id)
        stop_execution = datetime.datetime.utcnow()
        self._docker_answer.timing = SubTiming(description='start webdriver', start_execution=time_start, stop_execution=stop_execution, time=(stop_execution - time_start).total_seconds())

    @logging_and_timing()
    def _download_extensions(self):
        try:
            for extension_id in self._browser_config.extensions:
                self._logger.debug(f'Download extension {extension_id}')
                cache = self._redis_mongo_cache.get_value(str(extension_id))
                if not cache:
                    extension = BrowserExtension.objects.get(id=extension_id).only('extension_file')
                    cache = extension.extension_file.read()
                    self._redis_mongo_cache.setnx_value_pair(key=str(extension_id), value=cache)
                match self._browser_config.browser_options:
                    case ChromeUndectOptions():
                        zipfile.ZipFile(BytesIO(cache)).extractall(path=os.path.join(PLUGIN_DIR, str(uuid.uuid4())))
                    case _:
                        with open(os.path.join(PLUGIN_DIR, str(uuid.uuid4())), 'w+b') as file:
                            file.write(cache)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            return False
        return True

    @logging_and_timing()
    def _download_backup_profile(self, start_webdriver_cmd: StartWebdriverCMD):
        try:
            cache = self._redis_mongo_cache.get_value(str(start_webdriver_cmd.backup_profile_id)) or gridfs_get_data(
                db_name='Katti', object_id=start_webdriver_cmd.backup_profile_id).read()
            if cache:
                raise Exception(f'No profile in DB {str(start_webdriver_cmd.backup_profile_id)}')
            else:
                tar = TarFile(fileobj=io.BytesIO(cache))
                tar.extractall(INIT_PROFILE_DIR)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            return False
        return True

    def _start_browser_wrapper(self, start_back_up_id) -> WebdriverStartAnswer:
        self._logger.debug(f'Start browser wrapper.')
        match self._browser_config.browser_options:
            case ChromeOptions():
                wrapper_cls = ChromeWrapper
            case EdgeOptions():
                wrapper_cls = EdgeWrapper
            case ChromeUndectOptions():
                wrapper_cls = UndetectedChrome
            case ChromiumOptions():
                wrapper_cls = ChromiumWrapper
            case FirefoxOptions():
                wrapper_cls = FirefoxWrapper
            case _:
                return WebdriverStartAnswer(error_code=4206)
        try:
            self._browser_wrapper = wrapper_cls(browser_config=self._browser_config,
                                                logger=self._logger.getChild('browser_wrapper'),
                                                common_crawling_config=self._common_crawling_config)
            self._browser_wrapper.start_driver(
                start_profile_path=os.path.join(INIT_PROFILE_DIR, 'profile') if start_back_up_id else None)
            return WebdriverStartAnswer(error_code=0)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            return WebdriverStartAnswer(error_code=4207)

    @logging_and_timing()
    def _execute_iframe_fun_cmd(self, iframefun_cmd: IFrameFun):
        global EXTRA_DATA_FOR_DB
        iframe_worker = IFramesAreStupid2(logger=self._logger.getChild('iframe_worker'),
                                                config=self._common_crawling_config,
                                                plugin_mobile_phone=self._plugin_mobile_phone)
        iframe_worker.start(self.selenium_webdriver, perform_ad_clicks=iframefun_cmd.click_ads, mb=self._plugin_mobile_phone)
        EXTRA_DATA_FOR_DB.update({'iframe_fun': {
            'root_iframes': iframe_worker.root_iframes,
            'root_iframe_counter': len(iframe_worker.root_iframes),
            'child_iframes': iframe_worker.child_iframes,
            'child_iframes_counter': len(iframe_worker.child_iframes),
            'window_stats': iframe_worker.windows,
            'window_stats_counter': len(iframe_worker.windows)
        }})
        self._docker_answer = DockerAnswer(error_code=0)


    @logging_and_timing()
    def _execute_window_stats_cmd(self, window_stats_cmd: WindowStatsCMD):
        global WINDOW_STATS
        self._logger.debug(f'Start window tab pop up stuff. Count {self.selenium_webdriver.window_handles}')
        help = []
        main_window_handler = self.selenium_webdriver.current_window_handle
        try:
            new_window = self._browser_wrapper.build_window_object()
            new_window.action_id = f'{window_stats_cmd.action_id}'
            WINDOW_STATS.append(new_window)
            help.append(main_window_handler)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        finally:
            self.selenium_webdriver.switch_to.window(main_window_handler)
        for window_handler in self.selenium_webdriver.window_handles:
            if window_handler in help:
                continue
            try:
                self.selenium_webdriver.switch_to.window(window_handler)
                new_window = self._browser_wrapper.build_window_object()
                new_window.action_id = f'{window_stats_cmd.action_id}'
                WINDOW_STATS.append(new_window)
                help.append(window_handler)
            except Exception:
                self._logger.exception(traceback.format_exception(*sys.exc_info()))
            finally:
                self.selenium_webdriver.switch_to.window(main_window_handler)
        self._docker_answer = DockerAnswer(error_code=0)

    @logging_and_timing()
    def _execute_crawling_cmd(self, crawling_cmd: CrawlingCMD):
        if not self._browser_wrapper:
            self._logger.error('NO Browser init.')
            return
        self._next_crawling_cmd = crawling_cmd
        self._docker_answer = DockerAnswerCrawling()
        if self._proof_for_test_urls(crawling_cmd.crawling_url):
            return
        self._set_url_spezific_headers()
        self._logger.debug(f'Start loading URL {self._next_crawling_cmd.crawling_url} for bundle {self._next_crawling_cmd.bundle_id}')
        self._do_crawling()

    def _set_url_spezific_headers(self):
        with URL_LOCK:
            if self._browser_config.all_header_fields:
                HEADERS_ALL.extend(self._browser_config.all_header_fields)
            if self._browser_config.regex_headers:
                REGEX_HEADERS.extend(self._browser_config.regex_headers)
            header_cache = self._redis_mongo_cache.get_http_headers_for_crawling(bundle_id=self._next_crawling_cmd.bundle_id)
            if header_cache:
                HEADERS_ALL.extend(header_cache.header_fields_all)
                REGEX_HEADERS.extend(header_cache.header_fields_regex)

    def _do_crawling(self):
        del self.selenium_webdriver.requests
        error_code = 0
        try:
            self._do_crawl()
        except NameOrServiceNotKnownException:
            error_code = 4203
        except StatusCodeException:
            error_code = 4204
        except Exception:
            error_code = 4205
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        finally:
            self._docker_answer.error_code = error_code

    def _do_crawl(self):
        try:
            self._browser_wrapper.reset_browser_windows()
            self._logger.debug(f'Start crawling of {self._next_crawling_cmd.crawling_url}')
            self.selenium_webdriver.get(self._next_crawling_cmd.crawling_url)
        except TimeoutException:
            self._logger.debug(f'Timeout and check status code')
            self._docker_answer.was_timeout = True
            self._check_status_and_handle_bad_status()
        except Exception:
            raise
        else:
            self._check_status_and_handle_bad_status()

    def _check_status_and_handle_bad_status(self):
        self._get_status_code_main_url()
        if not self._akt_status_code_main_url:
            if (self._is_unkown_name_or_service()):
                self._logger.debug(f'Name or service not known')
                raise NameOrServiceNotKnownException('Name or service not known.')
            else:
                self._logger.debug(f'Bad status code')
                raise StatusCodeException()

    def _get_status_code_main_url(self):
        self._akt_status_code_main_url = None
        for sub_req in self.selenium_webdriver.requests:
            if sub_req.url.replace('/', '') == self._next_crawling_cmd.crawling_url.replace('/', ''):
                if sub_req.response:
                    self._akt_status_code_main_url = sub_req.response.status_code

    def _is_unkown_name_or_service(self):  # TODO check for
        ps = self.selenium_webdriver.find_elements(by=By.TAG_NAME, value='p')
        for p in ps:
            html = p.get_attribute('innerHTML')
            if 'Name or service not known' in html:
                return True
        return False

    def _shutdown_webbrowser(self):
        if self._browser_wrapper:
            self._logger.debug('Shutdown Webbrowswr-Wrapper')
            self._browser_wrapper.shutdown_driver()
            self._browser_wrapper = None
        if self._display:
            self._logger.debug('Close Display')
            self._display.stop()
            self._display = None

    def _proof_for_test_urls(self, url):
        x = False
        if 'katti.test_bad_status_code' in url:
            self._docker_answer.error_code = 4203
            x = True
        if 'katti.test_service_not_known' in url:
            self._docker_answer.error_code = 4204
            x = True
        if 'katti.test_unkown' in url:
            self._docker_answer.error_code = 4205
            x = True
        if 'katti.test_freeze' in url:
            time.sleep(5000000)

        return x