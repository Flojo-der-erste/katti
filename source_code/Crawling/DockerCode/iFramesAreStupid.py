import datetime
import sys
import time
import traceback
from copy import copy
from random import randint
import uuid
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.WindowTab import WindowTab
from DataBaseStuff.MongoengineDocuments.Crawling.iFrame import RootiFrame, ChildiFrame
from Crawling.DockerCode.PluginMobilePhone import PluginLogReceiver


class IFramesAreStupid2:
    def __init__(self, logger, config: CrawlingConfig, plugin_mobile_phone: PluginLogReceiver):
        self.driver = None
        self._logger = logger
        self._plugin_mobile_phone = plugin_mobile_phone
        self._visited_root_frames = None
        self._url = ''
        self._reload_counter = None
        self._start_windows = None

        self._new_root_frame = None
        self._max_wait_time_lef = 0

        self._config: CrawlingConfig = config
        self._should_perform_click_on_ad = True

    def start(self, driver, mb, perform_ad_clicks=True):
        self._max_wait_time_lef = copy(self._config.iframe_max_wait_time_for_all_frames)
        self._plugin_mobile_phone = mb
        self.driver = driver
        self._should_perform_click_on_ad = perform_ad_clicks

        self._akt_raw_iframes = []
        self.root_iframes = []
        self.child_iframes = []
        self.windows = []


        self._logger.debug(f'Lets do it!')
        self._reload_counter = 0
        self._visited_root_frames = []


        self._start_windows = self.driver.window_handles
        try:
            self._url = self.driver.current_url
            self.start_handle_iframes()
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        finally:
            self._logger.debug(f'First Window: {self._start_windows[0]}')
            self.driver.switch_to.window(self._start_windows[0])
            self._logger.debug(f'stop')


    def _scroll_to_element(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        #location = element.location
        #size = element.size
        #x = location['x'] + int(size['width']/2)
        #y = location['y'] - int(round(size['height'] / 2))
        #scroll_by_coord = 'window.scrollTo(%s,%s);' % (x, y)
        #self.driver.execute_script(scroll_by_coord)

    def _perform_click_on_ad(self, iframe: RootiFrame):
        click_reaction = 'nothing'
        click_action = RootiFrame.ClickAction(click_try_start=datetime.datetime.utcnow(), click_counter=0)
        iframe.click_action = click_action
        try:
            self._logger.debug(f'Start with click on ad.')
            self._scroll_to_element(iframe._raw_iframe)
            url_old = self.driver.current_url
            handles_old = self.driver.window_handles
            self._plugin_mobile_phone.reset_new_download()
            self._logger.debug(f'Click on ad, i = {click_action.click_counter}')
            action = ActionChains(self.driver)
            action.move_to_element(iframe._raw_iframe)
            action.click()
            action.perform()
            click_reaction = self._check_click_was_successful(url_old=url_old, handles=handles_old)
            while not click_reaction and click_action.click_counter < self._config.iframe_click_on_add_tries:
                click_action.click_time = datetime.datetime.utcnow()
                click_action.click_counter += 1
                self._logger.debug(f'Click on ad, i = {click_action.click_counter}')
                action = ActionChains(self.driver) #TODO: Nicht alle Webbrowser unterstützen das
                action.move_to_element_with_offset(iframe._raw_iframe, randint(3, int(iframe.width)-3), randint(3, int(iframe.height)-3))
                action.click()
                action.perform()
                click_reaction = self._check_click_was_successful(url_old=url_old, handles=handles_old)
                self._logger.debug(f'Clickreaction: {click_reaction}')
        except Exception:
            excp = traceback.format_exception(*sys.exc_info())
            self._logger.exception(f'Click on ad Exception:\n {excp}')
            click_action.click_exception = excp
            click_reaction = 'error'
        finally:
            click_action.click_try_stop = datetime.datetime.utcnow()
            click_action.click_result = click_reaction
            click_action.calculate_click_time()
        self._logger.debug(f'Finish click on ad')
        return click_action

    def _check_click_was_successful(self, handles, url_old):
        i = 0
        while i <= self._config.iframe_wait_for_click_reaction:
            if not self.driver.current_url == url_old:
                while i <= 10:
                    if self._check_for_download():
                        return 'url_changed_download'
                    time.sleep(0.1)
                    i += 1
                else:
                    return 'url_changed'
            elif not len(handles) >= len(self.driver.window_handles):
                return 'new_window'
            elif self._check_for_download():
                return 'download'
            time.sleep(0.1)
            i += 1
        return None

    def _check_for_download(self):
        if self._plugin_mobile_phone.get_new_download_started():
            return True
        else:
            return False

    def _check_if_iframe_ready(self, window_handler, frame):
        if not self._config.iframe_wait_for_frame_ready == 0:
            time.sleep(self._config.iframe_wait_for_frame_ready)
        self._config.iframe_wait_for_frame_ready = 0
        return True

    def start_handle_iframes(self):
        time_to_sleep = self._config.iframe_wait_before_start
        self._akt_depth = 1
        for index_h, handler in enumerate(self._start_windows):
            self.driver.switch_to.window(handler)
            window_url = self.driver.current_url
            self._akt_raw_iframes = self._build_root_frames(self.driver.find_elements(by=By.XPATH, value="//iframe"))
            self._logger.debug(f'found: {len(self._akt_raw_iframes)} iframes')
            self._akt_index = -1
            while len(self._akt_raw_iframes) > 0:
                if time_to_sleep > 0:
                    time.sleep(self._config.iframe_wait_before_start)
                    time_to_sleep = 0
                self._akt_index += 1
                self._logger.debug(f'start iframe with index {self._akt_index }')
                main_frame: RootiFrame = self._akt_raw_iframes.pop(0)
                main_frame.visits += 1
                if main_frame.visits > self._config.iframe_max_visits:
                    main_frame.max_visits = True
                    self.root_iframes.append(main_frame)
                    continue

                if not self._is_frame_big_enough(main_frame):
                    self._logger.debug(f'{main_frame._raw_iframe} not big enough')
                    continue
                elif not self._is_frame_visibility(main_frame):
                    self._logger.debug(f'{main_frame._raw_iframe} not visible')
                    continue
                elif not self._check_if_iframe_ready(handler, main_frame): #todo: Thing about retry
                        main_frame.not_ready = True
                        self._akt_raw_iframes.append(main_frame)
                        continue
                try:
                        main_frame.screenshot = main_frame._raw_iframe.screenshot_as_png
                except Exception:
                        self._logger.exception(traceback.format_exception(*sys.exc_info()))
                if self._was_root_iframe_visited(main_frame): #In case of reloading, only not visited iframes are interessting
                    self._logger.debug(f'iframe with index {self._akt_index} is in visited main frames.')
                    continue
                self.root_iframes.append(main_frame)
                try:
                    if not self._switch_to_iframe(main_frame):
                        main_frame.cant_switch = True
                        continue
                    self._set_tardis_tag(main_frame)
                    self._handle_nested_frame(main_frame.node_id)
                    self.driver.switch_to.default_content()
                    if self._should_perform_click_on_ad:
                        self._perform_click_on_ad(main_frame)
                    self._produce_windows()
                except StaleElementReferenceException:
                    self._logger.debug(f'iframe index {self._akt_index } StaleElementReferenceException')
                except Exception as e:
                    self._logger.exception(f'Exception, iframe index: {self._akt_index } \n {e}')
                finally:
                    self.driver.switch_to.window(handler)
                    self.driver.switch_to.default_content()
                    if not window_url == self.driver.current_url:
                        self._logger.debug(f'URL has changed, iframe index {self._akt_index }')
                        x = self._handle_url_changed(handler)
                        if x == 'handle next window':
                            break
                        if x == 'continue':
                            continue
                        if x == 'break':
                            return
                        self._produce_windows()
        self._produce_windows(end=True)

    def _was_root_iframe_visited(self, other_root_iframe):
        for root_iframe in self.root_iframes:
            if root_iframe == other_root_iframe:
                return True
        return False

    def _build_root_frames(self, raw_iframes) -> list:
        root_frames_for_handling = []
        for raw_iframe in raw_iframes:
            root_frames_for_handling.append(RootiFrame().build_from_raw_selenium_iframe(raw_iframe))
        return root_frames_for_handling

    def _handle_url_changed(self, akt_window_handler):
        self._logger.debug(f'URL changed {self.driver.current_url}')
        if not akt_window_handler == self._start_windows[0]: #URL change not in main window -> shit happens :)
            self._logger.debug(f'URL change not in main window -> shit happens :)')
            self._logger.debug(f'{self._start_windows}  {akt_window_handler}')
            return 'handle next window'
        elif self._reload_counter < self._config.iframe_max_reloads_url_changed: #TODO: Es wird nur Reload berücksichtigt und zwar der erste sonst einfadch true.
            self._akt_index = -1
            self._reload_counter += 1
            new_window = WindowTab(result_of_url_changed=True, depth=self._akt_depth, action_id='ad_fun')
            self.windows.append(new_window)
            try:
                new_window.set_window_features(self.driver, self._logger)
                self._logger.debug(f'Reload webpage original webpage')
                try:
                    self.driver.get(self._url) #todo: eventuell mit js location change und wait für ad_is_ready_tag. Besser für den Reload die Crawl url zu nehmen
                except TimeoutException:
                    self._logger.debug('Reload after url changed, timeoutexception')
                window = WindowTab(depth=self._akt_depth, action_id='ad_fun')
                self.windows.append(window)
                self._akt_raw_iframes = self._build_root_frames(self.driver.find_elements(by=By.XPATH, value="//iframe"))
                return 'continue'

            except Exception:
                self._logger.exception(traceback.format_exception(*sys.exc_info()))
                return 'break'

    def _produce_windows(self, end=False):
        time_buffer = self._config.iframe_sum_wait_for_read_ad_tag
        start_time = 0
        if len(self.driver.window_handles) - len(self._start_windows) >= self._config.iframe_min_windows_count_before_production or end:
            self._logger.debug(f'Start produce windows, windows: {len(self.driver.window_handles)}')
            for window in self.driver.window_handles:
                if window in self._start_windows:
                    continue
                new_window = WindowTab(depth=self._akt_depth, result_of_ad_click=True, action_id='ad_fun')
                self.windows.append(new_window)
                try:
                    start_time = time.time()
                    self.driver.switch_to.window(window)
                    try:
                        self._logger.debug(f'Start waiting for ad_is_ready_tag, winodw: {window}, time buffer: {time_buffer}')
                        WebDriverWait(self.driver, time_buffer).until(EC.presence_of_element_located((By.ID, 'add_is_ready_tag'))) #TODO: Ad-On coden, Insert after loaded ready
                    except TimeoutException:
                       new_window.ad_is_ready_timeout = True
                    new_window.set_window_features(self.driver, self._logger)
                    self._logger.debug(f'Produced window')
                except Exception:
                    self._logger.exception(traceback.format_exception(*sys.exc_info()))
                finally:
                    time_buffer = time_buffer - (time.time() - start_time)
                    if time_buffer < 1:
                        time_buffer = 1
                    try:
                        self._logger.debug(f'Closing window: {window}.')
                        self.driver.close()
                    except Exception:
                        self._logger.exception(traceback.format_exception(*sys.exc_info()))

    def _handle_nested_frame(self, parent_node_id):
        self._logger.debug(f'Handle nested iframes')
        nested_frames = self.driver.find_elements(by=By.XPATH, value="//iframe")
        self._logger.debug(f'found: {len(nested_frames)} nested iframes')
        for index, nested_frame in enumerate(nested_frames):
            new_child_frame = ChildiFrame(node_id=uuid.uuid4(), parent_node=parent_node_id, index=index, selenium_id=f'{nested_frame}')
            new_child_frame.iframe_page_source = self._get_outer_HTML(nested_frame)
            new_child_frame._raw_iframe = nested_frame
            self.child_iframes.append(new_child_frame)
            if not self._switch_to_iframe(new_child_frame):
                new_child_frame.produced = 'cant_switch'
                continue
            self._set_tardis_tag(new_child_frame)
            self._handle_nested_frame(new_child_frame.node_id)
            self.driver.switch_to.parent_frame()
        self._logger.debug('end function handle nested iframes')

    def _set_tardis_tag(self, frame_node):
        tardis_tag = ""
        try:
            tardis_tag = self.driver.find_element(by=By.ID, value='tardis_tag').get_attribute('innerHTML').split('Response from TARTDIS:')[1]
        except NoSuchElementException:
            self._logger.debug(f' No tardis tag')
        frame_node.tardis_tag = tardis_tag
        frame_node.parse_tardis_tag()

    def _switch_to_iframe(self, iframe):
        wait_time = self._max_wait_time_lef
        start = datetime.datetime.now()
        try:
            self._logger.debug(f'Switch to iFrame.')
            if wait_time <= 0:
                WebDriverWait(self.driver, 0.3).until(EC.frame_to_be_available_and_switch_to_it(iframe._raw_iframe))
            else:
                WebDriverWait(self.driver, wait_time).until(EC.frame_to_be_available_and_switch_to_it(iframe._raw_iframe))
        except TimeoutException:
            self._max_wait_time_lef -= (datetime.datetime.now() - start).seconds
            return False
        else:
            self._max_wait_time_lef -= (datetime.datetime.now() - start).seconds
            return True

    def _is_frame_visibility(self, iframe):
        wait_time = self._max_wait_time_lef
        start = datetime.datetime.now()
        try:
            self._logger.debug(f'Check if iFrame visible')
            if wait_time <= 0:
                WebDriverWait(self.driver, 0.3).until(EC.visibility_of(iframe._raw_iframe))
            else:
                WebDriverWait(self.driver, wait_time).until(EC.visibility_of(iframe._raw_iframe))
        except TimeoutException:
            self._max_wait_time_lef -= (datetime.datetime.now() - start).seconds
            return False
        else:
            self._max_wait_time_lef -= (datetime.datetime.now() - start).seconds
            return True

    def _is_frame_big_enough(self, frame: RootiFrame):
        if frame.height >= self._config.iframe_min_height and frame.width >= self._config.iframe_min_width:
            return True
        self._logger.debug(f'iframe is not big enough.')
        return False

    def _get_outer_HTML(self, iframe):
            return iframe.get_attribute('outerHTML')






