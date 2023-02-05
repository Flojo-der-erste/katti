from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BaseBrowserOptions import BaseBrowserOptions
from seleniumwire import webdriver


class FirefoxOptions(BaseBrowserOptions):
    """
    List of prefs: http://kb.mozillazine.org/About:config_entries
    """
    def get_webdriver_options_object(self, download_dir='', start_profile_path=''):
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.set_preference("pdfjs.disabled", True)
        match self.browser_privacy_level:
            case 'max_data':
                firefox_options.set_preference('network.cookie.cookieBehavior', 0) # 0: Enable all cookies (default) 1: Allow cookies from originating server only 2: Disable all cookies 3: Use P3P policy to decide (Mozilla Suite/SeaMonkey only)
                firefox_options.set_preference('privacy.trackingprotection.cryptomining.enabled', False)
                firefox_options.set_preference('privacy.trackingprotection.fingerprinting.enabled', False)
                firefox_options.set_preference('privacy.trackingprotection.pbmode.enabled', False)
            case 'privacy':
                firefox_options.set_preference('network.cookie.cookieBehavior', 2)
                firefox_options.set_preference('privacy.trackingprotection.cryptomining.enabled', True)
                firefox_options.set_preference('privacy.trackingprotection.fingerprinting.enabled', True)
                firefox_options.set_preference('privacy.trackingprotection.pbmode.enabled', True)
        if self.browser_safebrowsing:
            firefox_options.set_preference('browser.safebrowsing.enabled', True)
        else:
            firefox_options.set_preference('browser.safebrowsing.enabled', False)
        if self.preferences:
            for pref_name in self.preferences:
                firefox_options.set_preference(name=pref_name, value=self.preferences[pref_name])
        if self.command_line_switches:
            for cmd in self.command_line_switches:
                firefox_options.add_argument(cmd)
        return firefox_options