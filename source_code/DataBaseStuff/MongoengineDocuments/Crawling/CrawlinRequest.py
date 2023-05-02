import datetime
import uuid
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from mongoengine import DateTimeField, IntField, EmbeddedDocumentField, LazyReferenceField, \
    EmbeddedDocumentListField, StringField, ListField, EmbeddedDocument, BooleanField
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import PreCrawlingAnalyseSettings
from DataBaseStuff.MongoengineDocuments.Crawling.SpiderTrack import SpiderConfig
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData, Ownership


class BrowserGroup(EmbeddedDocument):
    browser_configs = ListField(required=True)
    group_id = StringField(default=f'{uuid.uuid4()}')


class CrawlingRequest(AbstractNormalDocument):
    meta = {'collection': 'crawling_requests'}

    @staticmethod
    def collection_name() -> str | None:
        return 'crawling_requests'

    start_time = DateTimeField(default=None)
    execute_urls_random = BooleanField(default=True)
    max_urls_per_group = IntField(min_value=1, default=20, max_value=150)
    spider_mode = EmbeddedDocumentField(SpiderConfig, default=None)

    infinity_run = BooleanField(default=False)
    ownership = EmbeddedDocumentField(Ownership, required=True)
    crawling_groups = EmbeddedDocumentListField(BrowserGroup, required=True)
    ignore_service_not_known_hours = IntField(default=24, min_value=0)

    dns_check = BooleanField(default=True)
    dns_check_valid_time = IntField(min_value=0, default=3600)
    katti_meta_data = EmbeddedDocumentField(MetaData, default=None)

    statefull_crawling = BooleanField(default=False)
    crawling_config = LazyReferenceField(CrawlingConfig, required=True)

    celery_task_id = StringField()
    status = StringField(choices=['running', 'finished', 'failure', 'break', 'aborted'], default='running')
    heartbeat = DateTimeField(default=datetime.datetime.utcnow())

    analyses_settings = EmbeddedDocumentField(PreCrawlingAnalyseSettings, default=None)
    operation_group_modi = StringField(choices=['waiting', 'not_waiting'], default='waiting')

    def set_heartbeat(self):
        if (datetime.datetime.utcnow() - self.heartbeat).total_seconds() > 60:
            self.heartbeat = datetime.datetime.utcnow()
            CrawlingRequest.objects(id=self.id).update_one(set__heartbeat=self.heartbeat)

    def set_init(self, status, celery_task_id):
        self.status = status
        self.celery_task_id = celery_task_id
        CrawlingRequest.objects(id=self.id).update_one(set__status=status, set__celery_task_id=str(celery_task_id))
