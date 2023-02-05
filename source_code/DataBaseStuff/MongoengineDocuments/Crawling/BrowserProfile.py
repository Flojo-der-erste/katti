from mongoengine import StringField, FileField
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument


class BrowserProfile(AbstractNormalDocument):
    name = StringField(required=True)
    for_browser = StringField(required=True, choices=['chrome'])
    browser_version = StringField(required=True, choices=['all'])
    tag_name = StringField()

    human_id = StringField()

    profile_file = FileField(required=True)