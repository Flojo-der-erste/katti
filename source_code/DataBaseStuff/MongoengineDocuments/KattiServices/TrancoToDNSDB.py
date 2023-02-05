from mongoengine import EmbeddedDocumentListField
from KattiServices.KattiDispatcherDocument import KattiServiceDB


class TrancoToDNSDB(KattiServiceDB):
    dns_execution_information = EmbeddedDocumentListField(DNSExecutionInformation, required=True)
