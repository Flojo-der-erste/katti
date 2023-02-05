import datetime
from mongoengine import EmbeddedDocument, EmbeddedDocumentField, ListField, StringField, \
    EmbeddedDocumentListField, BooleanField, IntField, ObjectIdField, DateTimeField
from pymongo import ReturnDocument

from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from DataBaseStuff.MongoengineDocuments.Crawling.BrowserAndExtension import BrowserExtension
from DataBaseStuff.MongoengineDocuments.Crawling.BrowserProfile import BrowserProfile
from DataBaseStuff.MongoengineDocuments.Crawling.HTTPRequestHeader import RegexHTTPRequestHeader, HTTPRequestHeader
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BaseBrowserOptions import BaseBrowserOptions
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.ChromiumBasedOptions import ChromeOptions
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.SeleniumWireOptions import SeleniumWireOptions


class BrowserConfig(AbstractNormalDocument):
    meta = {'collection': 'browser_configs'}

    class Config(EmbeddedDocument):
        selenium_wire_options = EmbeddedDocumentField(SeleniumWireOptions, default=SeleniumWireOptions())
        browser_options = EmbeddedDocumentField(BaseBrowserOptions, default=ChromeOptions())

        extensions = ListField()  # list[BrowserExtension.id]
        browser_profile_human_id = StringField()

        all_header_fields = EmbeddedDocumentListField(HTTPRequestHeader)
        regex_headers = EmbeddedDocumentListField(RegexHTTPRequestHeader)

        i_dont_care_about_cookies = BooleanField(default=True)

        window_size_x = IntField(default=1200)
        window_size_y = IntField(default=1900)

        simulating_user_actions = BooleanField(default=False)
        preprocessed_browser_profile = ObjectIdField(default=None)

        workflow = StringField(default='', choices=['with_iframe_fun_standalone', 'only_loading_standalone'])

        max_download_wait_time_s = IntField(min_value=0, default=60)
        page_load_timeout = IntField(min_value=1, default=30)
        loading_strategy = StringField(choices=['normal', 'eager', 'none'], default='normal')
        wait_after_crawl = IntField(min_value=0, default=1)

        @property
        def get_seleniumwire_options(self) -> SeleniumWireOptions:
            if self.browser_options.use_tor:
                self.selenium_wire_options.proxy = {
                    'http': 'socks5h://192.168.15.5:9050',
                    'https': 'socks5h://192.168.15.5:9050',
                    'connection_timeout': 10
                }
            return self.selenium_wire_options

        def get_extensions(self) -> list[BrowserExtension]:
            extensions = []
            for extension_id in self.extensions:
                try:
                    extensions.append(BrowserExtension.objects.get(id=extension_id))
                except Exception:
                    pass
            return extensions

        def get_human_like_browser_profile(self) -> BrowserProfile | None:
            if self.browser_profile_human_id:
                return BrowserProfile.objects.get(human_id=self.browser_profile_human_id)
            return None

    config = EmbeddedDocumentField(Config, required=True)
    create = DateTimeField(default=datetime.datetime.utcnow(), required=True)

    @property
    def browser_config(self) -> Config:
        return self.config

    @staticmethod
    def save_to_db(config: Config):
        return BrowserConfig.objects(config=config.to_mongo()).modify(set_on_insert__create=datetime.datetime.utcnow(),
                                                                      upsert=True,
                                                                      new=True)

    @staticmethod
    async def async_save_to_db(db, config: Config):
        x = await db['browser_configs'].find_one_and_update(filter={'config': config.to_mongo()},
                                                               update={'$setOnInsert': {'create': datetime.datetime.utcnow()}},
                                                               return_document=ReturnDocument.AFTER, upsert=True)
        x.update({'id': x.pop('_id')})
        return BrowserConfig(**x)

    @staticmethod
    def collection_name() -> str:
        return 'browser_configs'


