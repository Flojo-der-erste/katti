import datetime
import hashlib
from bson import ObjectId
from mongoengine import StringField, DateTimeField, DynamicEmbeddedDocument, \
    EmbeddedDocument, ObjectIdField, EmbeddedDocumentField
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument


class Ownership(EmbeddedDocument):
    owner = ObjectIdField(default=ObjectId()) #TODO: Change LazyRef. KattiUser


class Tag(AbstractNormalDocument):
    meta = {'collections': 'tags'}
    name = StringField(required=True)
    create = DateTimeField(required=True)
    ownership = EmbeddedDocumentField(Ownership, required=True)

    @staticmethod
    def create_tag(name, time_lord):
        Tag(name=name, create=datetime.datetime.utcnow(), ownership=Ownership(owner=time_lord.id))

class MetaData(DynamicEmbeddedDocument):
    tag = ObjectIdField()

    def __hash__(self):
        return int(hashlib.md5(self.to_json().encode()).hexdigest(), 16)