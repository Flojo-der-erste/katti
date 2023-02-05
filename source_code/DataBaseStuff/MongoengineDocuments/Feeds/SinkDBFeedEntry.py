#TODO: indicator bei awarness, allgemein angucken
from mongoengine import StringField, IntField, BooleanField, URLField

from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class SinkDBFeedEntry(BaseFeedEntry):
    classification = StringField(required=True)
    expose_vend = IntField(min_value=0, max_value=1)
    sinkdb_id = StringField()
    lea_only = BooleanField(default=False)

    expose_org = IntField()
    indicator = StringField()
    operator = StringField()
    sinkdb_reference = URLField()
    source = StringField()
    sinkdb_type = StringField()
    export = StringField()

    valid_from = StringField()
    valid_to = StringField()
    name = StringField()

    def _build_update_dict_for_update_one(self) -> dict:
        pass

    def _build_filter_dict_for_update_one(self) -> dict:
        pass

    def _get_filter_fields(self):
        return ['sinkddb_id', 'classification', 'expose_vend', 'lea_only']
