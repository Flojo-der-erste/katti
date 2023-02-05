import base64
import os.path
from Crawling.BrowserWrappers.BaseWebDriverWrapper import WebDriverWrapper
from Crawling.DockerCode.DockerKonstanten import DOWNLAD_DIR_STR, MAIN_DIR, GET_WEBDRIVER_EXECUATBLE_PATH, \
    SELENIUM_LOG_DIR
from seleniumwire import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService


class ChromiumBasedBrowserBase(WebDriverWrapper):
    @property
    def webdriver_cls(self):
        match self.browser_name:
            case 'chrome':
                return webdriver.Chrome
            case 'msedge':
                return webdriver.Edge

    @property
    def webdriver_service_obj(self):
        match self.browser_name:
            case 'chrome':
                return ChromeService(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('chrome'), log_path=SELENIUM_LOG_DIR,
                                     service_args=['--verbose'])
            case 'msedge':
                return EdgeService(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('msedge'), log_path=SELENIUM_LOG_DIR, service_args=['--verbose'])

    @property
    def browser_name(self) -> str:
        raise NotImplementedError

    @property
    def idcac_path(self):
        return os.path.join(MAIN_DIR, 'idontcareaboutcookies_chrome.crx')

    @property
    def katti_surv_path(self):
        return os.path.join(MAIN_DIR, 'katti_surv_chrome.crx')

    @property
    def _src_browser_profile_path(self) -> str:
        return self._selenium_driver.capabilities[self.browser_name]['userDataDir']

    def _before_webdriver_construction(self):
        self._logger.debug(f'Start {self.browser_name} driver with init browser profile: {self._start_profile_path}')
        self.webdriver_options_obj = self._browser_config.browser_options.get_webdriver_options_object(
            download_dir=DOWNLAD_DIR_STR,
            start_profile_path=self._start_profile_path)
        for extension_path in self._plugin_paths:
            self.webdriver_options_obj.add_extension(extension_path)
        if self._browser_config.i_dont_care_about_cookies:
            self.webdriver_options_obj.add_extension(self.idcac_path)
        self.webdriver_options_obj.add_extension(self.katti_surv_path)

    def _after_webdriver_construction(self):
        self._set_network_conditions()
        self._cdp_operations()

    def _cdp_operations(self):
        if self._browser_config.browser_options.geo_location:
            self._selenium_driver.execute_cdp_cmd("Emulation.setGeolocationOverride",
                                                  self._browser_config.browser_options.geo_location.__dict__)
        if self._browser_config.browser_options.device_metrics:
            self._selenium_driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                                                  {
                                                      "width": self._browser_config.window_size_x,
                                                      "height": self._browser_config.window_size_y,
                                                      "deviceScaleFactor": self._browser_config.browser_options.device_metrics.device_scale_factor,
                                                      "mobile": self._browser_config.browser_options.device_metrics.mobile
                                                  })
        self._selenium_driver.execute_cdp_cmd('Network.setCacheDisabled', {'cacheDisabled': True})

    def _set_network_conditions(self):
        if self._browser_config.browser_options.network_condition:
            self._selenium_driver.set_network_conditions(offline=False,
                                                         latency=self._browser_config.browser_options.network_condition.latency,
                                                         download_throughput=self._browser_config.browser_options.network_condition.download_throughput,
                                                         upload_throughput=self._browser_config.browser_options.network_condition.upload_throughput)

    def get_devtool_screenshot(self) -> bytes | None:
        resp = self._selenium_driver.execute_cdp_cmd('Page.captureScreenshot', {'captureBeyondViewport': True})
        return base64.b64decode(resp['data'])

    @staticmethod
    def _own_request_interceptor(request):
        pass

    @staticmethod
    def _own_response_interceptor(request, response):
        pass
