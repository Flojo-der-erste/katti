from mongoengine import EmbeddedDocument, StringField, IntField, BooleanField, LazyReferenceField, ListField, \
    EmbeddedDocumentListField
from DataBaseStuff.MongoengineDocuments.Crawling.Link import Link
from DataBaseStuff.MongoengineDocuments.Crawling.OutsourcedData import OutsourcedData


class WindowTab(EmbeddedDocument):
    url = StringField()
    tab_id = StringField()
    window_id = StringField()

    selenium_id = StringField()
    tardis_tag = StringField()
    action_id = StringField()
    depth = IntField(min_value=1, default=1)

    screenshot_js = LazyReferenceField(document_type=OutsourcedData, default=None)
    screenshot_dcp = LazyReferenceField(document_type=OutsourcedData, default=None)
    page_source = LazyReferenceField(document_type=OutsourcedData, default=None)
    viewport_screenshot = LazyReferenceField(document_type=OutsourcedData, default=None)

    ad_window_fun_window = BooleanField(default=False)

    ad_is_ready_timeout = BooleanField()
    result_of_url_changed = BooleanField()
    result_of_ad_click = BooleanField()

    links = EmbeddedDocumentListField(Link, default=[])

    _help_screen_js = None
    _help_screenshot_dcp = None
    _help_page_source = None
    _help_viewport = None

    def save_it(self):
        if self._help_screen_js:
            self.screenshot_js = OutsourcedData.build(data=self._help_screen_js, source='crawling')
        if self._help_screenshot_dcp:
            self.screenshot_dcp = OutsourcedData.build(data=self._help_screenshot_dcp, source='crawling')
        if self._help_page_source:
            self.page_source = OutsourcedData.build(data=self._help_page_source.encode(), source='crawling')
        if self._help_viewport:
            self.viewport_screenshot = OutsourcedData.build(data=self._help_viewport, source='crawling')