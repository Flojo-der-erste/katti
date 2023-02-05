import datetime
from pymongo import UpdateOne
from mongoengine import LazyReferenceField, DateTimeField, IntField, DynamicDocument
from DataFeeds.BaseDataFeed import BaseDataFeed


class BaseFeedEntry(DynamicDocument):
    meta = {'abstract': True, 'db_alias': 'Katti'}

    feed = LazyReferenceField(BaseDataFeed)
    counter = IntField()
    ttl = DateTimeField(default=datetime.datetime.utcnow())

    _with_feed = True
    _with_validation = True

    def get_update_one(self):
        if self._with_validation:
            self.validate()
        if self._with_feed:
            filter = {'feed': self.feed}
        else:
            filter = {}
        filter.update(self._build_filter_dict_for_update_one())
        return UpdateOne(filter=filter, update=self._build_update_dict_for_update_one(), upsert=True)

    def _build_update_dict_for_update_one(self) -> dict:
        raise NotImplementedError

    def _build_filter_dict_for_update_one(self) -> dict:
        raise NotImplementedError
