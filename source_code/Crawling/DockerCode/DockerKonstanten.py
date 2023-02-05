import os


BACKUP_BROWSER_PROFILE_STR = 'backup_browser_profile'
INIT_BROWSER_PROFILE_STR = 'init_browser_profile'
PLUGIN_DIR_STR = 'plugins'
SELENIUM_LOG_DIR_STR = 'selenium_logs'
DOWNLAD_DIR_STR = 'download_dir'

MAIN_DIR = os.path.expanduser('~/')

INIT_PROFILE_DIR = os.path.join(MAIN_DIR, f'{INIT_BROWSER_PROFILE_STR}/')
PLUGIN_DIR = os.path.join(os.path.expanduser('~/'), f'{PLUGIN_DIR_STR}/')
SELENIUM_LOG_DIR = os.path.join(os.path.expanduser('~/'), f'{SELENIUM_LOG_DIR_STR}/logs.log')
DOWNLAOD_DIR = os.path.join(os.path.expanduser('~/'), f'{DOWNLAD_DIR_STR}/')

GET_WEBDRIVER_EXECUATBLE_PATH = lambda name: os.path.join(os.path.expanduser('~/'), f'{name}driver')