from mongoengine import ListField, IntField

from KattiServices.KattiDispatcherDocument import KattiServiceDB


class BundleAnalyseTaskStarter(KattiServiceDB):
    running_tasks = ListField()
    max_running_tasks = IntField(min_value=1, default=10000)