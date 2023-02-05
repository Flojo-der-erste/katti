import os.path
from selenium.webdriver.firefox.service import Service
from Crawling.BrowserWrappers.BaseWebDriverWrapper import WebDriverWrapper
from Crawling.DockerCode.DockerKonstanten import GET_WEBDRIVER_EXECUATBLE_PATH, DOWNLAD_DIR_STR, \
    MAIN_DIR
from seleniumwire import webdriver


class FirefoxWrapper(WebDriverWrapper):

    @property
    def idcac_path(self):
        return os.path.join(MAIN_DIR, 'idontcareaboutcookies.xpi')


    @property
    def katti_surv_extension_name(self):
        return os.path.join(MAIN_DIR, 'katti_surv_chrome.xpi')

    @property
    def _src_browser_profile_path(self) -> str:
        return self.driver.capabilities['moz:profile']

    @property
    def webdriver_cls(self):
        return webdriver.Firefox

    @property
    def webdriver_service_obj(self):
        return Service(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('gecko'))

    @property
    def browser_name(self) -> str:
        return 'gecko'

    def _before_webdriver_construction(self):
        self.webdriver_options_obj = self._browser_config.browser_options.get_webdriver_options_object(
            download_dir=DOWNLAD_DIR_STR, start_profile_path=self._start_profile_path)

    def _after_webdriver_construction(self):
        for extension_path in self._plugin_paths:
            self._selenium_driver.install_addon(extension_path)
        if self._browser_config.i_dont_care_about_cookies:
           self._selenium_driver.install_addon(self.idcac_path)
        self._selenium_driver.install_addon(self.katti_surv_extension_name)


    # def _read_ind_MIME_types(self):
    #     mime_types = ''
    #     with open(os.path.join(FILES, 'mime_types')) as file:
    #         lines = file.readlines()
    #         for line in lines:
    #            mime_type = line.rstrip()
    #           mime_types += f'{mime_type}'
    #  return mime_types


   # def _click_on_button(self, xpath, enabled=False):
   #     radio = self._selenium_driver.find_element_by_xpath(xpath)
   #     if radio.is_selected() and not enabled:
   #         radio.click()
   #     if not radio.is_selected() and enabled:
   #         radio.click()
