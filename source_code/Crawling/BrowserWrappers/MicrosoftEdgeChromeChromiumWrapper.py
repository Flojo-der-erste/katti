from Crawling.BrowserWrappers.ChromiumBasedBrowserBase import ChromiumBasedBrowserBase
import seleniumwire.undetected_chromedriver as uc
from Crawling.DockerCode.DockerKonstanten import GET_WEBDRIVER_EXECUATBLE_PATH, SELENIUM_LOG_DIR


class EdgeWrapper(ChromiumBasedBrowserBase):

    @property
    def browser_name(self) -> str:
        return 'msedge'


class ChromeWrapper(ChromiumBasedBrowserBase):
    @property
    def browser_name(self) -> str:
        return 'chrome'


class UndetectedChrome(ChromiumBasedBrowserBase):
    def _construction_of_webdriver(self):
        self.webdriver_options_obj.page_load_strategy = self._browser_config.loading_strategy
        self._selenium_driver = uc.Chrome(
            options=self.webdriver_options_obj,
            driver_executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('chrome'),
            service_args=['--verbose'],
            service_log_path=SELENIUM_LOG_DIR,
            seleniumwire_options=self._browser_config.get_seleniumwire_options.to_mongo()
        )

    @property
    def browser_name(self) -> str:
        return 'chrome_undect'


class ChromiumWrapper(ChromiumBasedBrowserBase):
    @property
    def browser_name(self) -> str:
        return 'chrome'
