import datetime
from mongoengine import DateTimeField, BooleanField, IntField, ObjectIdField

from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractDynamicalDocument


class BaseStatistics(AbstractDynamicalDocument):
    meta = {'abstract': True,
            'db_alias': 'Katti'}


class BaseTaskStatistics(BaseStatistics):
    meta = {'collection': 'service_statistics',
            'allow_inheritance': True}

    start_time = DateTimeField(default=datetime.datetime.utcnow(), required=True)
    stop_time = DateTimeField(required=True)

    run_time = IntField(default=0)
    error = BooleanField(default=False)
    service_id = ObjectIdField()
    ttl = DateTimeField(default=datetime.datetime.utcnow())

    @classmethod
    def get_task_with_times(cls, service_id):
        return cls(service_id=service_id,
                   ttl=datetime.datetime.utcnow(),
                   start_time=datetime.datetime.utcnow())

    def stop_and_save(self):
        self.stop_time = datetime.datetime.utcnow()
        self.run_time = (self.stop_time - self.start_time).microseconds
        self.save()
