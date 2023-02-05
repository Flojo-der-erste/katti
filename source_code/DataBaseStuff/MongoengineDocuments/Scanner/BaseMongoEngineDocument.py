import datetime
from bson import ObjectId, SON
from mongoengine import StringField, BooleanField, LazyReferenceField, IntField, \
    DateTimeField, EmbeddedDocumentField, DynamicField, EmbeddedDocumentListField
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument, AbstractDynamicalDocument
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData, Ownership


def get_last_valid_result(result_cls, ooi: str, scanner_id: ObjectId, ttl: int):
    return result_cls.objects(ooi=ooi,
                              scanner=scanner_id,
                              id__gte=ObjectId.from_datetime(
                                  (datetime.datetime.utcnow() - datetime.timedelta(seconds=ttl)))).modify(
        inc__access_counter=1, upsert=False)


class BaseScannerDocument(AbstractNormalDocument):
    meta = {'collection': 'scanner',
            'allow_inheritance': True}

    type = StringField(required=True)
    active = BooleanField(default=True)
    time_valid_response = IntField(default=24 * 60 * 60)
    max_wait_time_for_cache = IntField(default=5)
    name = StringField(required=True, unique=True)


class BaseScanningRequests(AbstractDynamicalDocument):
    meta = {'abstract': True}
    ownership = EmbeddedDocumentField(Ownership, required=True)
    scanner = LazyReferenceField(BaseScannerDocument, required=True)
    ooi = DynamicField(required=True)
    katti_meta_data = EmbeddedDocumentListField(MetaData)
    katti_create = DateTimeField()
    quota_exception = StringField(default=None)

    @classmethod
    def build_new_request(cls, ooi, scanner, ownership, meta_data=None, **kwargs):
        if meta_data is None:
            meta_data = []
        else:
            meta_data = [meta_data]
        new_re = cls(katti_create=datetime.datetime.utcnow(), ooi=ooi, scanner=scanner, katti_meta_data=meta_data,
                     ownership=ownership, **kwargs)
        return new_re

    def update_exiting_request_in_db(self, new_meta_data_as_SON: SON):
        raise NotImplementedError


class BaseScanningResults(AbstractDynamicalDocument):
    meta = {'abstract': True}

    katti_create = DateTimeField()
    katti_last = DateTimeField()
    Katti_meta_data = EmbeddedDocumentListField(MetaData)
    ooi = StringField()

    @classmethod
    def get_result_from_db(cls, scanner_obj, filter: dict, ooi, update=None, set_on_insert_dict: dict = None):
        if update is None:
            update = {}
        if scanner_obj.meta_data_as_son:
            BaseScanningResults._expand_update(update_key='$addToSet',
                                               update={'katti_meta_data': scanner_obj.meta_data_as_son},
                                               mongodb_update=update)
        BaseScanningResults._expand_update(update_key='$set',
                                           update={'katti_last': datetime.datetime.utcnow()},
                                           mongodb_update=update)
        BaseScanningResults._expand_update(update_key='$setOnInsert',
                                           update={'katti_create': datetime.datetime.utcnow(),
                                                   'scanner': scanner_obj._scanner_document.id}, mongodb_update=update)
        if ooi:
            BaseScanningResults._expand_update(update_key='$setOnInsert',
                                               update={'ooi': str(ooi)}, mongodb_update=update)
        if set_on_insert_dict:
            BaseScanningResults._expand_update(update_key='$setOnInsert',
                                               update=set_on_insert_dict, mongodb_update=update)
        return cls.objects(**filter).modify(__raw__=update,
                                            upsert=True,
                                            new=True)

    @staticmethod
    def _expand_update(update_key, update: dict, mongodb_update: dict):
        if update_key in mongodb_update:
            mongodb_update[update_key].update(update)
        else:
            mongodb_update.update({update_key: update})
