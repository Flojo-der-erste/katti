from mongoengine import Document, StringField, DateTimeField, IntField, LazyReferenceField, DictField

from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord


class FastAPIStats(Document):
    endpoint = StringField()
    start_time = DateTimeField()
    stop_time = DateTimeField()
    run_time_ms = IntField()
    request = DictField()
    user = LazyReferenceField(TimeLord)
