from pymongo import UpdateOne
from DataFeeds.TrancoFeed.TrancoFeed import TrancoFeedEntry
from DataBaseStuff.MongoengineDocuments.KattiServices.TrancoToDNSDB import TrancoToDNSDB
from KattiServices.SourceToScannerService.SourceToScannerBase import SourceToScannerBase


class TrancoToDNS(SourceToScannerBase):
    db_document: TrancoToDNSDB

    @property
    def db_document_cls(self):
        return TrancoToDNSDB

    def _execute_next_round(self):
        self._to_update_bulk_ops = []
        self._get_new_tranco_entries_and_append_to_dns()

    def _end_of_round(self):
        TrancoFeedEntry()._get_collection.bulk_write(self._to_update_bulk_ops)

    def _get_new_tranco_entries_and_append_to_dns(self):
        self._add_new_entry_to_dns(TrancoFeedEntry.objects(__raw__={f'to_dns_service_visit.{self.db_document.id}': False}).only('domain')[:50000])

    def _add_new_entry_to_dns(self, entries: list[TrancoFeedEntry]):
        for entry in entries:
            self._to_update_bulk_ops.append(UpdateOne({'_id': entry.id}, {'$set': {f'to_dns_service_visit.{self.db_document.id}': True}}))
            self._add_to_builders(ooi=entry.domain)

