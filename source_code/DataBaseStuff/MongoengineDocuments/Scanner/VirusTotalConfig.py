from mongoengine import StringField, EmbeddedDocumentField
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument
from Scanner.QuotaMechanic import MongoDBQuota


class VirusTotalConfig(BaseScannerDocument):
    api_key = StringField(required=True)
    vt_user = StringField(required=True)
    quota = EmbeddedDocumentField(MongoDBQuota)