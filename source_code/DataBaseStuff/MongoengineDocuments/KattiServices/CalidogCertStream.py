from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractDynamicalDocument
from mongoengine import BooleanField, IntField, StringField
from KattiServices.KattiDispatcherDocument import KattiServiceDB


class CalidogCerstreamEntry(AbstractDynamicalDocument):
    meta = {'collection': 'calidog_ct_logs'}


class CaliDogCertStreamDB(KattiServiceDB):
    X509LogEntry = BooleanField(default=True)
    PrecertLogEntry = BooleanField(default=False)
    entries_before_bulk = IntField(default=1000, min_value=10)
    certstream_url = StringField(default='wss://certstream.calidog.io/')