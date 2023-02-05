import datetime
import uuid
from mongoengine import EmbeddedDocument, StringField, EmbeddedDocumentListField, UUIDField, IntField, BooleanField, \
    DynamicField, EmbeddedDocumentField, DateTimeField
from selenium.webdriver.remote.webelement import WebElement
from Crawling.Constants import TARDIS_TAG


class IsMalicious(EmbeddedDocument):
    pass


class Iframe(EmbeddedDocument):
    meta = {'allow_inheritance': True}
    node_id = UUIDField()
    is_malicious = EmbeddedDocumentField(IsMalicious)
    is_advertising = BooleanField(default=None)

    iframe_page_source = StringField()
    iframe_outer_html = StringField(default="default")
    tardis_tag = StringField(default="")

    tab_id = StringField()
    window_id = StringField()
    url = StringField()
    selenium_id = StringField()

    def parse_tardis_tag(self):
        if not self.tardis_tag == "":
            for tag in self.tardis_tag.split(' '):
                print(tag)
                key, value = tag.split(TARDIS_TAG)
                match key:
                    case 'tab_id':
                        self.tab_id = value
                    case 'window_id':
                        self.window_id = value
                    case 'url':
                        self.url = value


class ChildiFrame(Iframe):
    frame_type = StringField(choices=['root', 'child'], default='root')
    node_id = UUIDField()
    parent_node = UUIDField()

    index = IntField()
    _raw_iframe: WebElement = None


class RootiFrame(Iframe):
    class ClickAction(EmbeddedDocument):
        click_result = StringField(choices=['nothing', 'download', 'new_window', 'url_changed', 'error', 'url_changed_download'], default=None)
        click_time = IntField()
        click_exception = StringField(default=None)
        click_try_start = DateTimeField()
        click_try_stop = DateTimeField()
        click_counter = IntField()

        def calculate_click_time(self):
            if self.click_try_stop and self.click_try_start:
                self.click_time = (self.click_try_stop - self.click_try_start).microseconds

    parent_window_selenium_id = StringField()
    child_nodes = EmbeddedDocumentListField(ChildiFrame)
    child_counter = IntField(min_value=0, default=0)
    new_add_window_stats = DynamicField()
    screenshot = DynamicField()
    height = DynamicField(default=-10)
    width = DynamicField(default=-10)

    visits = IntField(default=0, min_value=0)

    not_ready = BooleanField(default=False)
    max_visits = BooleanField(default=False)
    cant_switch = BooleanField(default=False)

    click_action = EmbeddedDocumentField(ClickAction)

    _raw_iframe: WebElement = None
    _last_visit = datetime.datetime.utcnow()
    def set_loacation(self, location):
        self.height = location['height']
        self.width = location['width']

    def build_from_raw_selenium_iframe(self, raw_iframe: WebElement):
        self.node_id = uuid.uuid4()
        self._raw_iframe = raw_iframe
        self.selenium_id = f'{raw_iframe}'
        try:
            self.set_loacation(raw_iframe.size)
        except Exception:
            pass
        try:
            self.iframe_outer_html = raw_iframe.get_attribute('outerHTML')
        except Exception:
            pass
        return self

    def __eq__(self, other):
        if not (isinstance(other, self.__class__)):
            return False
        if self.height == other.height and self.width == other.width:
            return True
        return False



