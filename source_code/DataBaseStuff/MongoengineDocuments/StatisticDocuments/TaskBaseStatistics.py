import datetime

from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership
from mongoengine import DateTimeField, BooleanField, IntField, StringField, DynamicDocument, \
    EmbeddedDocumentField, FloatField


class BaseStatistics(DynamicDocument):
    meta = {'abstract': True,
            'db_alias': 'Katti'}


class BaseTaskStatistics(BaseStatistics):
    meta = {'collection': 'task_statistics',
            'allow_inheritance': True}

    start_time = DateTimeField(default=datetime.datetime.utcnow(), required=True)
    stop_time = DateTimeField(required=True)

    run_time = FloatField()
    error = BooleanField(default=False)
    retry_exception = BooleanField(default=False)
    retry_counter = IntField(default=0, min_value=0)

    task_id = StringField(required=True)
    ttl = DateTimeField(default=datetime.datetime.utcnow())
    ownership = EmbeddedDocumentField(Ownership)


    @classmethod
    def get_task_with_times(cls, task_id, initiator, **kwargs):
        return cls(task_id=task_id,
                   ttl=datetime.datetime.utcnow(),
                   start_time=datetime.datetime.utcnow(),
                   initiator=initiator,
                   **kwargs)

    def stop_and_save(self):
        self.stop_time = datetime.datetime.utcnow()
        self.run_time = (self.stop_time - self.start_time).total_seconds()
        self.save()
