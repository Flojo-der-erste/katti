import datetime
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from croniter import croniter
from mongoengine import IntField, EmbeddedDocumentField, BinaryField, DateTimeField, ValidationError
from pymongo import UpdateOne, DeleteOne
from DataBaseStuff.MongoengineDocuments.IntervalCronTab import Interval, CronTab
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData


class CommonScannerRequest(AbstractNormalDocument):
    max_lookups = IntField(default=1, min_value=0)
    priority = IntField(min_value=0, max_value=3, default=0)
    last_lookup = DateTimeField()
    next_lookup = DateTimeField(default=datetime.datetime.utcnow())
    lookups = IntField(default=0, min_value=0)
    ownership = EmbeddedDocumentField(Ownership)
    meta_data = EmbeddedDocumentField(MetaData)

    interval = EmbeddedDocumentField(Interval, default=Interval())
    cron_tab = EmbeddedDocumentField(CronTab)

    celery_task_signature = BinaryField(required=True)

    @classmethod
    def get_next_signatures_for_execution(cls, limit=5000):
        pipline = [{'$match': {'next_lookup': {'$lte': datetime.datetime.utcnow()}}},
                   {'$sort': {'execution_information.priority': -1, 'next_lookup': 1}},
                   {'$limit': limit}]
        return [cls._from_son(raw_candidate) for raw_candidate in list(cls.objects().aggregate(pipline))]

    def set_lookup_and_cal_next(self) -> UpdateOne | DeleteOne:
        time = datetime.datetime.utcnow()
        self.last_lookup = time
        self.lookups += 1
        if self.lookups < self.max_lookups or self.max_lookups == 0:
            self._calculate_next_lookup_time()
            return UpdateOne({'_id': self.id}, {'$set': {'last_lookup': self.last_lookup,
                                                         'next_lookup': self.next_lookup,
                                                         'lookups': self.lookups}})
        else:
            return DeleteOne({'_id': self.id})

    def _calculate_next_lookup_time(self):
        if self.interval:
            match self.interval.period:
                case 'day':
                    self.next_lookup = (datetime.datetime.utcnow() + datetime.timedelta(
                        days=self.interval.every))
        else:
            iter = croniter(self.cron_tab.to_string(), datetime.datetime.utcnow())
            self.next_lookup = iter.get_next(datetime.datetime)

    def clean(self):
        try:
            x = self.__getattribute__('execution_information')
        except Exception:
            raise ValidationError('execution_information must be implemented')