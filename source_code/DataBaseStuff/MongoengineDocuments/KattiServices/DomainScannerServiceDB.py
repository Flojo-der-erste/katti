from mongoengine import BooleanField, ListField, EmbeddedDocumentListField
from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import DNSExecutionInformation, \
    BaseExecutionInformation
from KattiServices.KattiDispatcherDocument import KattiServiceDB


class DomainDGAScanner(KattiServiceDB):
    dga_source = ListField(default=['360', 'fkie'])
    overwrite = BooleanField(default=False)
    execution_information = EmbeddedDocumentListField(BaseExecutionInformation, required=True)
    force_insert = BooleanField(default=True)

