from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from mongoengine import BooleanField, DateTimeField, IntField, LazyReferenceField, EmbeddedDocumentListField, EmbeddedDocumentField

from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import BrowserGroup
from DataBaseStuff.MongoengineDocuments.Crawling.SpiderTrack import SpiderConfig
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord
from KattiServices.KattiDispatcherDocument import KattiServiceDB



class CrawlingServiceDB(KattiServiceDB):
    meta = {'collection': 'crawling_requests',
            'db_alias': 'Katti'}

    start_time = DateTimeField(default=None)
    execute_urls_random = BooleanField(default=True)
    max_urls_per_group = IntField(min_value=1, default=20, max_value=150)
    spider_mode = EmbeddedDocumentField(SpiderConfig, default=None)

    infinity_run = BooleanField(default=False)
    owner = LazyReferenceField(TimeLord)
    crawling_groups = EmbeddedDocumentListField(BrowserGroup, default=[], required=True)
    first_run = BooleanField(default=True)
    ignore_service_not_known_hours = IntField(default=24, min_value=0)

    ignore_blacklist_direct_match = BooleanField(default=False)
    ignore_blacklist_domain_match = BooleanField(default=False)

    statefull_crawling = BooleanField(default=False)
    crawling_config = LazyReferenceField(CrawlingConfig, required=True)


    def save(self, force_insert=False, validate=True, clean=True, write_concern=None, cascade=None, cascade_kwargs=None,
             _refs=None, save_condition=None, signal_kwargs=None, **kwargs):
        return super().save(force_insert, validate, clean, write_concern, cascade, cascade_kwargs, _refs,
                            save_condition, signal_kwargs, **kwargs)

    #url_list_build_pipline = ListField(default=['one_time', 'static', 'tranco', 'dynamical'])