import datetime
import uuid
from croniter import croniter
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from mongoengine import EmbeddedDocument, EmbeddedDocumentListField, ObjectIdField, EmbeddedDocumentField, StringField, \
    BooleanField, IntField, DateTimeField, ListField

from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import BaseExecutionInformation


class AnalyseTask(EmbeddedDocument):
    execution_information = EmbeddedDocumentField(BaseExecutionInformation)
    task_id = StringField(default=f'{uuid.uuid4()}')


class PreCrawlingAnalyseSettings(EmbeddedDocument):
    analyse_tasks = EmbeddedDocumentListField(AnalyseTask, required=True)

    priority = IntField(min_value=0, max_value=3, default=0)
    internal_links = BooleanField(default=True)
    external_links = BooleanField(default=True)
    social_media_links = BooleanField(default=False)


class BundleAnalysesTracking(EmbeddedDocument):
    counter = IntField(min_value=0, default=0)
    last_execution = DateTimeField()
    next_execution = DateTimeField()
    running_tasks = ListField()
    task_id = StringField(required=True)


    @property
    def it_is_time(self) -> bool:
        return not self.next_execution or datetime.datetime.utcnow() >= self.next_execution

    def set_and_calculate_next(self, analysis_settings: AnalyseTask) -> None | datetime.datetime:
        time = datetime.datetime.utcnow()
        self.last_execution = time
        self.counter += 1
        if analysis_settings.execution_information.max_lookups == 1:
            return None
        if analysis_settings.execution_information.max_lookups < self.counter or analysis_settings.execution_information.max_lookup == 0:
            self._calculate_next_lookup_time(analysis_settings)
            return self.next_execution
        else:
            return None

    def _calculate_next_lookup_time(self, analysis_settings: AnalyseTask):
        if analysis_settings.execution_information.interval:
            match analysis_settings.execution_information.interval.period:
                case 'day':
                    self.next_execution = (datetime.datetime.utcnow() + datetime.timedelta(days=analysis_settings.execution_information.interval.every))
        else:
            iter = croniter(analysis_settings.execution_information.cron_tab.to_string(), datetime.datetime.utcnow())
            self.next_execution = iter.get_next(datetime.datetime)


class BundleAnalyseCandidate(AbstractNormalDocument):
    next_execution = DateTimeField(required=True)
    bundle_id = ObjectIdField(required=True)
    priority = IntField(min_value=0, max_value=3, default=0)
    saw_you = BooleanField(default=False)