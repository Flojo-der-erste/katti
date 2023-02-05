from bson import ObjectId
from CeleryBeatMongo.models import Interval, Crontab
from DataBaseStuff.ConnectDisconnect import connect_to_database
from mongoengine import IntField, ListField
from PerodicSystemTasks.BasePerodicSystemTask import BasePeriodicSystemTask


class DatabaseStatsCalculation(BasePeriodicSystemTask):
    scale = IntField(default=1024 + 1024, min_value=1024)
    skip_dbs = ListField(default=['Katti'])
    skip_collections = ListField(default=['DatabaseStats'])

    @classmethod
    def build(cls, period, **kwargs):
        new_stat = cls(task='CeleryApps.PeriodicSystemTasks.db_stats')
        if isinstance(period, Interval):
            new_stat.interval = period
        elif isinstance(period, Crontab):
            new_stat.crontab = period
        else:
            raise Exception
        self_id = ObjectId()
        args = [str(self_id)]
        new_stat.id = self_id
        new_stat.args = args
        new_stat.run_immediately = kwargs.get('run_immediately', True)
        new_stat.visible = kwargs.get('visible', True)
        return new_stat


if __name__ == '__main__':
    connect_to_database()
    new_ = DatabaseStatsCalculation.build(Crontab(minute='0', hour='23'))
    new_.save()
