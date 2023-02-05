import datetime
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from croniter import croniter
from mongoengine import DateTimeField, IntField, ListField, EmbeddedDocumentListField, ObjectIdField, EmbeddedDocumentField, ValidationError, LazyReferenceField
from pymongo import UpdateOne, DeleteOne
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest
from DataBaseStuff.MongoengineDocuments.Crawling.HTTPRequestHeader import HTTPRequestHeader, RegexHTTPRequestHeader
from DataBaseStuff.MongoengineDocuments.IntervalCronTab import Interval, CronTab


class URLForCrawling(AbstractNormalDocument):
    meta = {'allow_inheritance': True, 'collection': 'urls_for_crawling',
            'indexes': [('crawling_request_id')]}

    @staticmethod
    def collection_name() -> str | None:
        return 'urls_for_crawling'

    urls = ListField(required=True)
    crawling_request_id = LazyReferenceField(CrawlingRequest, required=True, dbref=False)

    all_header_fields = EmbeddedDocumentListField(HTTPRequestHeader)
    regex_headers = EmbeddedDocumentListField(RegexHTTPRequestHeader)


    max_lookups = IntField(min_value=0, default=1)
    last_lookup = DateTimeField()
    next_lookup = DateTimeField(default=datetime.datetime.utcnow())
    lookup_counter = IntField(min_value=0, default=0)

    interval = EmbeddedDocumentField(Interval, default=None)
    cron_tab = EmbeddedDocumentField(CronTab)

    def clean(self):
        if not self.max_lookups == 1:
            if self.interval and self.cron_tab:
                raise ValidationError('Cannot define both interval and crontab schedule.')
            if not (self.interval or self.cron_tab):
                raise ValidationError('Must defined either interval or crontab schedule.')
            if len(self.urls) <= 0:
                raise ValidationError('We need urls :)')
            for url in self.urls:
                if not isinstance(url, str):
                    raise ValidationError(f'We need valid urls :) {url}')

    def set_lookup_and_cal_next(self) -> UpdateOne | DeleteOne:
        self.lookup_counter += 1
        self.last_lookup = datetime.datetime.utcnow()
        if self.lookup_counter < self.max_lookups or self.max_lookups == 0:
            self._calculate_next_lookup_time()
            return UpdateOne({'_id': self.id}, {'$set': {'last_lookup': self.last_lookup,
                                                         'next_lookup': self.next_lookup,
                                                         'lookup_counter': self.lookup_counter}})
        else:
            return DeleteOne({'_id': self.id})

    def _calculate_next_lookup_time(self):
        if self.interval:
            match self.interval.period:
                case 'day':
                    self.next_lookup = (datetime.datetime.utcnow() + datetime.timedelta(days=self.interval.every))
                case'seconds':
                    self.next_lookup = (datetime.datetime.utcnow() + datetime.timedelta(seconds=self.interval.every))
        else:
            iter = croniter(self.cron_tab.to_string(), datetime.datetime.utcnow())
            self.next_lookup = iter.get_next(datetime.datetime)


class URLForCrawlingLink(URLForCrawling):
    master_bundle = ObjectIdField(required=True)
    origin_bundle = ObjectIdField(required=True)
    deep = IntField(required=True)