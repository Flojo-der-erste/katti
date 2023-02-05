import datetime

from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import BundleAnalysesTracking

from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractDynamicalDocument
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.Link import URL
from DataBaseStuff.MongoengineDocuments.Crawling.OutsourcedData import OutsourcedData
from DataBaseStuff.MongoengineDocuments.Crawling.WindowTab import WindowTab
from mongoengine import StringField, LazyReferenceField, ListField, EmbeddedDocument, \
    DateTimeField, EmbeddedDocumentField, EmbeddedDocumentListField, BooleanField, IntField, \
    LongField, DynamicField, ObjectIdField, FloatField
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData


class CeleryCrawlingOpData(EmbeddedDocument):
    celery_task_id = StringField()
    docker_container_name = StringField()
    crawling_step = StringField(choices=['start', 'end'])
    docker_restart_counter = IntField(min_value=0, default=0)
    url_retry_counter = IntField(min_value=0, default=0)

    successfull_crawling = BooleanField(default=False)
    statefull_retry = BooleanField(default=None)

    exceptions = ListField()

class SubTiming(EmbeddedDocument):
    description = StringField()
    start_execution = DateTimeField()
    stop_execution = DateTimeField()
    time = FloatField()


class CrawlingTimings(EmbeddedDocument):
    complete_start_time = DateTimeField(default=datetime.datetime.utcnow())
    complete_stop_time = DateTimeField(default=datetime.datetime.utcnow())
    complete_time_ms = LongField()

    sub_timings = EmbeddedDocumentListField(SubTiming)


class BeforeNavigateLog(EmbeddedDocument):
    timestamp = DynamicField()
    nav_url = DynamicField()
    tab_id = DynamicField()
    frame_id = DynamicField()
    parent_frame = DynamicField()

    @classmethod
    def build(cls, raw_log):
        new_log = cls(parent_frame=raw_log['parent_frame'],
                      nav_url=raw_log['nav_url'],
                      tab_id=raw_log['tab_id'],
                      frame_id=raw_log['frame_id'],
                      timestamp=raw_log['timestamp'])
        return new_log


class NewTabLog(EmbeddedDocument):
    window_id = IntField()
    tab_id = IntField()
    url = StringField()
    title = StringField()
    timestamp = DynamicField()

    @classmethod
    def build(cls, raw_log):
        new_log = cls(window_id=raw_log['window_id'],
                      tab_id=raw_log['tab_id'],
                      url=raw_log['url'],
                      title=raw_log['title'],
                      timestamp=raw_log['timestamp'])
        return new_log


class NewWindowLog(EmbeddedDocument):
    window_id = StringField()
    window_type = StringField()
    timestamp = DynamicField()

    @classmethod
    def build(cls, raw_log):
        new_log = cls(window_id=raw_log['window_id'],
                      window_type=raw_log['window_type'],
                      timestamp=raw_log['timestamp'])
        return new_log


class HandleAlarmLog(EmbeddedDocument):
    info = StringField()
    timestamp = DynamicField()

    @classmethod
    def build(cls, raw_log):
        new_log = cls(info=raw_log['info'],
                      timestamp=raw_log['timestamp'])
        return new_log


class ExtensionInstallationLog(EmbeddedDocument):
    homepage_url = StringField()
    host_permissions = ListField()
    install_type = StringField()
    name = StringField()
    permissions = StringField()
    type = StringField()
    timestamp = DynamicField()

    @classmethod
    def build(cls, raw_log):
        new_log = cls(homepage_url=raw_log.get('homepageUrl'),
                      host_permissions=raw_log.get('hostPermissions'),
                      install_type=raw_log.get('installType'),
                      name=raw_log.get('name'),
                      permissions=raw_log.get('permissions'),
                      type=raw_log.get('type'),
                      timestamp=(raw_log.get('timestamp')))
        return new_log


class DownloadLog(EmbeddedDocument):
        download_id = StringField()
        filename = StringField()
        complete = StringField()
        start_time = DateTimeField()
        url = StringField()
        mime_type = StringField()


class KattiSurveillanceLogs(EmbeddedDocument):
    download_logs = EmbeddedDocumentListField(DownloadLog)
    extension_install_logs = EmbeddedDocumentListField(ExtensionInstallationLog)
    alarm_logs = EmbeddedDocumentListField(HandleAlarmLog)
    new_window_logs = EmbeddedDocumentListField(NewWindowLog)
    new_tab_logs = EmbeddedDocumentListField(NewTabLog)
    navigation_logs = EmbeddedDocumentListField(BeforeNavigateLog)
    unknown_logs = ListField()


class Bundle(AbstractDynamicalDocument):
    meta = {'collection': 'bundles'}

    class Screenshot(EmbeddedDocument):
        screenshot = LazyReferenceField(document_type=OutsourcedData)
        snap_time = DateTimeField()
        tab_id = StringField()
        tag = StringField(choices=['after_load', 'after_ad'])


    class CrawlingMeta(EmbeddedDocument):
        crawling_request_id = ObjectIdField(required=True)
        group_id = StringField()
        ownership = EmbeddedDocumentField(Ownership, required=True)
        katti_meta_data = EmbeddedDocumentField(MetaData)
        analyses_tracking = EmbeddedDocumentListField(BundleAnalysesTracking)
        celery_task_status = EmbeddedDocumentField(CeleryCrawlingOpData)

        blocked = StringField(choices=['url_blacklist', 'nxdomain', 'service_not_known', 'no', 'ip_blocked'], default='no')
        browser_config = LazyReferenceField(BrowserConfig)
        crawling_config = LazyReferenceField(CrawlingConfig)
        create = DateTimeField(default=datetime.datetime.utcnow())

        crawling_timings = EmbeddedDocumentField(CrawlingTimings)

        statefull_id = ObjectIdField()
        statefull_index = IntField()


    def update_celery_task_status(self, status_objc: CeleryCrawlingOpData):
        self.crawling_meta_data.celery_task_status = status_objc
        Bundle.objects(id=self.id).update_one(__raw__={'$set': {'crawling_meta_data.celery_task_status': status_objc.to_mongo()}})

    def update_analysis_tracking(self):
        Bundle.objects(id=self.id).update_one(__raw__={'$set': {'crawling_meta_data.analyses_tracking': self.crawling_meta_data.analyses_tracking.to_mongo()}})


    crawling_url = EmbeddedDocumentField(URL, required=True)
    requests_count = IntField(default=0)
    download_count = IntField(default=0)
    requests = ListField()
    browser_profile = ObjectIdField()
    window_tab_pop_attributes = EmbeddedDocumentListField(WindowTab)
    window_pop_tab_counter = IntField(default=0)



    crawling_meta_data = EmbeddedDocumentField(CrawlingMeta)
    katti_surveillance_logs = EmbeddedDocumentField(KattiSurveillanceLogs)





