from mongoengine import IntField

from DataBaseStuff.MongoengineDocuments.StatisticDocuments.TaskBaseStatistics import BaseTaskStatistics


class FeedTaskStatistics(BaseTaskStatistics):
    entries_counter = IntField()