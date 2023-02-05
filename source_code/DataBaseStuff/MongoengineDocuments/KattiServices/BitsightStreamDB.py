import datetime
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractDynamicalDocument, AbstractNormalDocument
from mongoengine import StringField, DateTimeField, IntField, ListField, URLField, DictField
from pymongo import UpdateOne
from KattiServices.KattiDispatcherDocument import KattiServiceDB


class BitsightStreamDB(KattiServiceDB):
    feed_url = URLField(required=True)
    api_key = StringField(required=True)

    group = ListField(default=[])
    fields = ListField(default=[])
    origin = ListField(default=[])
    modules = ListField(default=[])
    filters = DictField(default={})
    group_time = IntField(min_value=1, default=600)

    last_api_disconnection = DateTimeField(default=datetime.datetime.utcnow())
    disconnection_interval_hours = IntField(default=2, min_value=1)

    check_kill_timer_every_seconds = IntField(default=10, min_value=1)


class BitsightStreamEntry(AbstractDynamicalDocument):
    meta = {'collection': 'bitsight',
            'indexes': [{'fields': ['bs_timestamp', 'src', 'dst'],
                         'name': 'main_bitsight'}]}

    src = DictField()
    dst = DictField()
    geo_src_ip = DictField()
    group = DictField()
    bs_timestamp = DateTimeField()


class BitsightFamilyEntry(AbstractNormalDocument):
    meta = {'collection': 'bitsight_families'}

    family = StringField()
    counter = IntField()
    days = ListField()
    first_seen = DateTimeField()

    min_severity = IntField()
    max_severity = IntField()

    categories = ListField()

    @staticmethod
    def build_update_one(family, severity, bitsight_timestamp=datetime.datetime.utcnow(), categories=[]):
        return UpdateOne(filter={'family': family},
                         update={'$addToSet': {
                             'days': datetime.datetime.strptime(f'{bitsight_timestamp.date()} 00:00:00',
                                                                '%Y-%m-%d %H:%M:%S'),
                             'categories': {'$each': categories}},
                                 '$setOnInsert': {'first_seen': bitsight_timestamp},
                                 '$min': {'min_severity': severity},
                                 '$max': {'max_severity': severity},
                                 '$inc': {'counter': 1}},
                         upsert=True)
