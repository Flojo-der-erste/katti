from mongoengine import ObjectIdField, StringField, ListField, EmbeddedDocument, IntField, BooleanField, \
    EmbeddedDocumentField, ValidationError
from DataBaseStuff.MongoengineDocuments.IntervalCronTab import Interval, CronTab


class BaseExecutionInformation(EmbeddedDocument):
    meta = {'allow_inheritance': True}
    time_valid_response = IntField(min_value=0, default=0)
    max_lookups = IntField(default=1, min_value=0)
    priority = IntField(min_value=0, max_value=3, default=0)
    interval = EmbeddedDocumentField(Interval, default=Interval())
    cron_tab = EmbeddedDocumentField(CronTab)


    def clean(self):
        if self.interval and self.cron_tab:
            msg = 'Cannot define both interval and crontab schedule.'
            raise ValidationError(msg)
        if not (self.interval or self.cron_tab) and not self.max_lookups == 1:
            msg = 'Must defined either interval or crontab schedule.'
            raise ValidationError(msg)


class DNSExecutionInformation(BaseExecutionInformation):
    scanner_id = ObjectIdField(required=True)
    dig_type = StringField(default='ANY')
    dig_flags = ListField()


class GSBExecutionInformation(BaseExecutionInformation):
    scanner_id = ObjectIdField(required=True)  # ObjectIDs


class SSLScannerExecutionInformation(BaseExecutionInformation):
    scanner_id = ObjectIdField(required=True)


class ShodanExecutionInformation(BaseExecutionInformation):
    scanner_id = ObjectIdField(required=True)


class VirusTotalExecutionInformation(BaseExecutionInformation):
    scanner_id = ObjectIdField(required=True)
    endpoint = StringField(required=True)