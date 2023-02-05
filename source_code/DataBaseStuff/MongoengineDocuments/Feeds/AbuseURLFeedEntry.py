import datetime
from mongoengine import EmbeddedDocument, StringField, DateTimeField, IntField, DynamicField, BooleanField, \
    EmbeddedDocumentListField
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class AbuseURLHausEntry(BaseFeedEntry):
    meta = {'collection': 'abuse_url',
            'indexes': [{'fields': ['abuse_id', 'url_status', 'last_online', 'threat'],
                         'name': 'main_abuse'}]}

    class Update(EmbeddedDocument):
        status = StringField()
        day = DateTimeField()

    @property
    def entry_insert_index(self):
        return 'main_abuse'

    abuse_id = IntField()
    threat = StringField(default=None)
    tags = DynamicField(default=None)
    date_added = DateTimeField(default=None)
    url = StringField(default=None)
    urlhaus_link = StringField(default=None)
    reporter = StringField(default=None)
    last_online = DateTimeField(default=None)
    error = BooleanField()
    updates = EmbeddedDocumentListField(document_type=Update,
                                        default=[])

    _with_feed = False
    @classmethod
    def build(cls, raw_data: dict):
        global DAY
        raw_data.update({'abuse_id': int(raw_data['abuse_id'])})
        raw_data.update({'date_added': datetime.datetime.strptime(raw_data['date_added'], '%Y-%m-%d %H:%M:%S')})
        raw_data.update({'tags': raw_data['tags'].split(',')})
        if raw_data['last_online'] == 'None':
            raw_data.update({'last_online': None})
        else:
            try:
                raw_data.update({'last_online': datetime.datetime.strptime(raw_data['last_online'].replace('X', '0'), '%Y-%m-%d %H:%M:%S')})
            except Exception:
                raw_data.update({'error': True})
        update = AbuseURLHausEntry.Update(status=raw_data.get('url_status', ''), day=DAY)
        del raw_data['url_status']
        new = cls(**raw_data)
        new.updates.append(update)

    def _build_update_dict_for_update_one(self):
        mongo = self.to_mongo()
        mongo.pop('abuse_id')
        return {'$addToSet': {'days': {'$each': mongo.pop('updates')}},
                '$setOnInsert': mongo}

    def _build_filter_dict_for_update_one(self) -> dict:
        return  {'abus_id': self.abuse_id}