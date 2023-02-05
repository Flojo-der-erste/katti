from mongoengine import BooleanField, IntField

from KattiServices.KattiDispatcherDocument import KattiServiceDB


class CrawlingAnalysesDB(KattiServiceDB):
    wait_time_for_dns_results = IntField(min_value=1, default=20)