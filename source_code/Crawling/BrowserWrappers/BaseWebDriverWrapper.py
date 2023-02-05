import os
import re
import sys
import threading
import traceback
from os.path import isfile, join
from urllib.parse import urlparse

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from Crawling.Constants import TARDIS_TAG
from Crawling.DockerCode.DockerKonstanten import INIT_PROFILE_DIR
from Crawling.Utils.JavaScriptScreenshot import screenshot_full_page
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.HTTPRequestHeader import HTTPRequestHeader, RegexHTTPRequestHeader
from DataBaseStuff.MongoengineDocuments.Crawling.Link import Link
from DataBaseStuff.MongoengineDocuments.Crawling.WindowTab import WindowTab
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from Utils.HelperFunctions import is_valid_url
from seleniumwire import webdriver

HEADERS_ALL: list[HTTPRequestHeader] = []
REGEX_HEADERS: list[RegexHTTPRequestHeader] = []
URL_LOCK = threading.Lock()


class WebDriverWrapper:
    def __init__(self, logger, browser_config: BrowserConfig.Config, common_crawling_config: CrawlingConfig):
        self._logger = logger
        self._selenium_driver: webdriver = None
        self._browser_config: BrowserConfig.Config = browser_config
        self._common_config:CrawlingConfig = common_crawling_config
        self.webdriver_options_obj = None
        self._start_profile_path = None

    @property
    def driver(self) -> webdriver:
        return self._selenium_driver


    @property
    def _src_browser_profile_path(self) -> str:
        raise NotImplementedError

    @property
    def webdriver_cls(self):
        raise NotImplementedError

    @property
    def webdriver_service_obj(self):
        raise NotImplementedError

    @property
    def browser_name(self) -> str:
        """Name of webdriver browser. Chrome -> chrome, Edge -> msedge"""
        raise NotImplementedError

    def _before_webdriver_construction(self):
        raise NotImplementedError

    def _after_webdriver_construction(self):
        raise NotImplementedError

    def get_devtool_screenshot(self) -> bytes | None:
        return None

    def _get_plugin_paths_to_install(self) -> list[str]:
        only_files = [f for f in os.listdir(INIT_PROFILE_DIR) if isfile(join(INIT_PROFILE_DIR, f))]
        return only_files

    def _construction_of_webdriver(self):
        if not self.webdriver_options_obj:
            raise Exception('Upps you did something wrong :). We need an options object.')
        self.webdriver_options_obj.page_load_strategy = self._browser_config.loading_strategy
        self._selenium_driver = self.webdriver_cls(
            service=self.webdriver_service_obj,
            options=self.webdriver_options_obj,
            seleniumwire_options=self._browser_config.get_seleniumwire_options.to_mongo())

    def get_requests_response_pairs(self):
        return [request for request in self._selenium_driver.requests]

    def shutdown_driver(self):
        self._logger.debug(f'Shutdown')
        if self._selenium_driver:
            try:
                self._selenium_driver.quit()
            except Exception as e:
                self._logger.error(f'Problems Shutdown Driver: {e} ')

    def start_driver(self, start_profile_path: str | None = None) -> webdriver:
        self._start_profile_path = start_profile_path
        self._plugin_paths = self._get_plugin_paths_to_install()
        self._before_webdriver_construction()
        self._construction_of_webdriver()
        self._prepare_driver()
        self._after_webdriver_construction()
        return self._selenium_driver

    def _prepare_driver(self):
        self._selenium_driver.set_page_load_timeout(self._browser_config.page_load_timeout)
        self._selenium_driver.set_window_size(self._browser_config.window_size_x, self._browser_config.window_size_y)
        self._selenium_driver.request_interceptor = WebDriverWrapper._request_interceptor
        self._selenium_driver.response_interceptor = WebDriverWrapper._response_interceptor

    def reset_browser_windows(self):
        window_handles = self._selenium_driver.window_handles
        self._logger.debug(f'Before reset Window-Handler count: {len(window_handles)}')
        self.close_windows(window_handles[1:])
        self._selenium_driver.switch_to.window(window_handles[0])
        self._selenium_driver.get("about:blank")
        self._logger.debug(f'After reset Window-Handler count: {len(self._selenium_driver.window_handles)}')

    def close_windows(self, windows):
        self._logger.debug(f'Start closing windows')
        i = 0
        while i < len(windows):
            self._selenium_driver.switch_to.window(windows[i])
            self._selenium_driver.close()
            i += 1

    def build_window_object(self) -> WindowTab:
        new_window_tab_obj = WindowTab()
        try:
            new_window_tab_obj._help_viewport = self._selenium_driver.get_screenshot_as_png()
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        try:
            new_window_tab_obj._help_screen_js = screenshot_full_page(driver=self._selenium_driver, lo=self._logger).getvalue()
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        try:
            pass
           # new_window_tab_obj._help_screenshot_dcp = self.get_devtool_screenshot()
        except:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        try:
            new_window_tab_obj.selenium_id = self._selenium_driver.current_window_handle
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))

        try:
            new_window_tab_obj._help_page_source = self._selenium_driver.page_source
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        try:
            new_window_tab_obj.url = self._selenium_driver.current_url
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        try:
            domain = urlparse(self._selenium_driver.current_url).netloc
            for link in self._selenium_driver.find_elements(By.TAG_NAME, 'a'):
                href = link.get_attribute('href')
                if is_valid_url(href):
                    new_link = Link.build(href)
                    if domain == urlparse(href).netloc:
                        new_link.kind = 'intern'
                    else:
                        new_link.kind = 'extern'
                    new_window_tab_obj.links.append(new_link)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        tardis_tag = None
        try:
            tardis_tag = self._selenium_driver.find_element(by=By.ID, value='tardis_tag').get_attribute('innerHTML').split('Response from TARTDIS:')[1]
            self._produce_tardis_tag(tardis_tag)
        except NoSuchElementException:
            tardis_tag = 'NoSuchElementException'
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        finally:
            self.tardis_tag = tardis_tag
        return new_window_tab_obj

    def _produce_tardis_tag(self, tardis_tag):
        for tag in tardis_tag.split(' '):
            key, value = tag.split(TARDIS_TAG)
            match key:
                case 'tab_id':
                    self.tab_id = value
                case 'window_id':
                    self.window_id = value
                case 'url':
                    self.url = value

    @staticmethod
    def _own_request_interceptor(request):
        """Override for own behaviour"""
        pass

    @staticmethod
    def _request_interceptor(request):
        global HEADERS_ALL, REGEX_HEADERS, URL_LOCK
        with URL_LOCK:
            for header in HEADERS_ALL:
                header_add_or_delete(request, header)
            for regex_header in REGEX_HEADERS:
                if re.match(regex_header.regex, request.url):
                    for single_header in regex_header.header_fields:
                        header_add_or_delete(request, single_header)
            WebDriverWrapper._own_request_interceptor(request)

    @staticmethod
    def _own_response_interceptor(request, response):
        """Override for own behaviour"""
        pass

    @staticmethod
    def _response_interceptor(request, response):
        WebDriverWrapper._own_response_interceptor(request, response)


def header_add_or_delete(request, header):
    del request.headers[header.header_field]
    if header.add:
        request.headers[header.header_field] = header.header_value