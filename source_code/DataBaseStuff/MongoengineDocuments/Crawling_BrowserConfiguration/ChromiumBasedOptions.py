from selenium.webdriver.chromium.options import ChromiumOptions
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BaseBrowserOptions import ChromiumBasedOptions
from seleniumwire import webdriver
from selenium.webdriver.edge.options import Options as WebdriverEdgeOptions
import seleniumwire.undetected_chromedriver as uc


def common_chromium_settings(webdriver_options_obj: ChromiumOptions, options: ChromiumBasedOptions, profile_path: str=None, ):
    webdriver_options_obj.add_argument('--no-sandbox')
    webdriver_options_obj.add_argument('--disable-dev-shm-usage')
    webdriver_options_obj.add_argument('--disable-gpu')
    if profile_path:
        webdriver_options_obj.add_argument(f'--user-data-dir={profile_path}')
    for switch in options.command_line_switches:
        webdriver_options_obj.add_argument(switch)


class ChromeOptions(ChromiumBasedOptions):

    def get_webdriver_options_object(self, download_dir='', start_profile_path=None) -> webdriver.ChromeOptions:
        ops = webdriver.ChromeOptions()
        common_chromium_settings(ops, self, profile_path=start_profile_path)
        prefs = dict(self.preferences)
        if self.browser_safebrowsing:
            prefs.update({'safebrowsing.enabled': False})
        ops.add_experimental_option("prefs", prefs)
        return ops


class ChromeUndectOptions(ChromiumBasedOptions):
    def get_webdriver_options_object(self, download_dir='', start_profile_path=''):
        ops = uc.ChromeOptions()
        common_chromium_settings(ops, self, profile_path=start_profile_path)
        prefs = dict(self.preferences)
        if self.browser_safebrowsing:
            prefs.update({'safebrowsing.enabled': False})
        ops.add_experimental_option("prefs", prefs)
        return ops


class ChromiumOptions(ChromiumBasedOptions):
    def get_webdriver_options_object(self, download_dir='', start_profile_path=None) -> webdriver.ChromeOptions:
        ops = webdriver.ChromeOptions()
        ops.binary_location = '/usr/bin/chromium'
        common_chromium_settings(ops, self, profile_path=start_profile_path)
        prefs = dict(self.preferences)
        if self.browser_safebrowsing:
            prefs.update({'safebrowsing.enabled': False})
        ops.add_experimental_option("prefs", prefs)
        return ops


class EdgeOptions(ChromiumBasedOptions):
    def get_webdriver_options_object(self, download_dir='', start_profile_path='') -> WebdriverEdgeOptions:
        ops = WebdriverEdgeOptions()
        common_chromium_settings(ops, self, profile_path=start_profile_path)
        ops.add_argument("--proxy-server=127.0.0.1:30004")
        ops.accept_insecure_certs = True
        prefs = dict(self.preferences)
        if self.browser_safebrowsing:
            ops.add_argument("--disable-features=msSmartScreenProtection")
        match self.browser_privacy_level:
            case 'max_data':
                prefs.update({'enhanced_tracking_prevention': {'enabled': False}})
                prefs.update({'do_not_track': False})
            case 'privacy':
                prefs.update({'enhanced_tracking_prevention': {'enabled': True, 'user_pref': 2}})
                prefs.update({'do_not_track': True})
        ops.add_experimental_option("prefs", prefs)
        return ops