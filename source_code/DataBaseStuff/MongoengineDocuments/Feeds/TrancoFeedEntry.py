from mongoengine import EmbeddedDocument, DateTimeField, IntField, StringField, EmbeddedDocumentListField, BooleanField
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class TrancoFeedEntry(BaseFeedEntry):
    meta = {'collection': 'tranco_entries', 'db_alias': 'Katti',
            'indexes': [{'fields': ['domain'],
                         'name': 'domain'}]}

    class DayRank(EmbeddedDocument):
        day = DateTimeField()
        rank = IntField()

    domain = StringField(required=True)
    day_ranks = EmbeddedDocumentListField(DayRank)
    to_dns_service_visit = BooleanField(default=False)

    _with_feed = False

    def _build_filter_dict_for_update_one(self) -> dict:
        return {'domain': self.domain}

    def _build_update_dict_for_update_one(self):
        return {'$addToSet': {'day_ranks': {'$each': self.to_mongo()['day_ranks']}},
                '$setOnInsert': {'to_dns_service_visit': False}}