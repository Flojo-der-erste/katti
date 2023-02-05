from mongoengine import ListField, IntField

from KattiServices.KattiDispatcherDocument import KattiServiceDB


class CommonScannerRequestStarter(KattiServiceDB):
    running_tasks = ListField()
    max_running_tasks = IntField(min_value=1, max_value=500, required=True)