from mongoengine import IntField, ObjectIdField
from DataBaseStuff.MongoengineDocuments.StatisticDocuments.TaskBaseStatistics import BaseTaskStatistics

class GSBScannerTaskStatistics(BaseTaskStatistics):
    urls_count = IntField(min_value=0)

    urls_left_over = IntField(min_value=0, default=0)
