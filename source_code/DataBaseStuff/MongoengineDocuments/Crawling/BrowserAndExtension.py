from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from mongoengine import StringField, FileField, ListField


class BrowserExtension(AbstractNormalDocument):
    meta = {'collection': 'supported_extensions'}
    name = StringField(required=True)
    version = StringField(required=True)
    description = StringField(required=True)
    supported_browser = ListField(default=['chrome', 'edge', 'chromium'], required=True)

    extension_file = FileField(db_alias='Katti')


class Browser(AbstractNormalDocument):
    meta = {'collection': 'supported_browser'}
    name = StringField(choices=['Chrome', 'Edge', 'Firefox', 'Chromium', 'undect_chrome'], unique=True)
    description = StringField()
    version = StringField(required=True)