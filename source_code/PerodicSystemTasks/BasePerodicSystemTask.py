from CeleryBeatMongo.models import PeriodicTask


class BasePeriodicSystemTask(PeriodicTask):
    meta = {'allow_inheritance': True}

