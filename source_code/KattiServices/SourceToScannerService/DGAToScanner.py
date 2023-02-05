import datetime
from pymongo import UpdateOne
from DataBaseStuff.MongoengineDocuments.Feeds.DGAEntry import DGAEntry
from KattiServices.SourceToScannerService.SourceToScannerBase import SourceToScannerBase
from DataBaseStuff.MongoengineDocuments.KattiServices.DomainScannerServiceDB import DomainDGAScanner


class DomainDGAScannerService(SourceToScannerBase):
    db_document: DomainDGAScanner

    @property
    def db_document_cls(self):
        return DomainDGAScanner

    def _execute_next_round(self):
        self._to_update_bulk_ops = []
        self._scanner_requests_insert = []
        self._day = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
        self._get_next_domains()

    def _end_of_round(self):
        if len(self._to_update_bulk_ops) > 0:
            DGAEntry()._get_collection.bulk_write(self._to_update_bulk_ops)

    def _get_next_domains(self):
        self.logger.debug('Get next domains')
        raw = {'$or': [{f'last_to_dns_visit.{self.db_document.id}': {'$exists': False}},
                       {f'last_to_dns_visit.{self.db_document.id}': {'$lt': self._day}}],
               'activity': {'$elemMatch': {'day': self._day,
                                           'dga_source': {'$in': ['fkie', '360']}}}}
        self._insert_domains_for_dns(DGAEntry.objects(__raw__=raw)[:50000])

    def _insert_domains_for_dns(self, next_domains: list[DGAEntry]):
        for domain_obj in next_domains:
            self._add_to_builders(ooi=domain_obj.domain, meta_data={'family': domain_obj.family, 'dga_sources': list(set([act.dga_source for act in domain_obj.activity]))}) #TODO: WHY?!?!?!?!?
            self._to_update_bulk_ops.append(UpdateOne({'_id': domain_obj.id}, {'$set': {f'last_to_dns_visit.{self.db_document.id}': self._day}}))



