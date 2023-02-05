from mongoengine import StringField, DateTimeField, EmbeddedDocument, EmbeddedDocumentListField, DynamicField
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class DGAEntry(BaseFeedEntry):
    meta = {'collection': 'dga_entries',
            'indexes': [{'fields': ['family', 'domain'],
                         'name': 'domain_family'}]}

    class DGAMeta(EmbeddedDocument):
        day = DateTimeField(required=True)
        dga_source = StringField(choices=['360', 'fkie', 'bambenek'], required=True)
        extra_info = DynamicField()

    domain = StringField(required=True)
    family = StringField(required=True)
    activity = EmbeddedDocumentListField(DGAMeta, default=[])

    start_360 = DateTimeField(default=None)
    end_360 = DateTimeField(default=None)

    _with_feed = False


    def _build_update_dict_for_update_one(self):
        update = {'$addToSet': {'activity': {'$each': self.to_mongo()['activity']}},
                  '$setOnInsert': {'create': self.ttl}}
        if self.start_360 and self.end_360:
            update.update({'$min': {'start_360': self.start_360},
                           '$max': {'end_360': self.end_360}
                           })

        return update

    def _build_filter_dict_for_update_one(self) -> dict:
        return {'family': self.family, 'domain': self.domain}


