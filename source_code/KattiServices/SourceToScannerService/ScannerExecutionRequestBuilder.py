import pickle
from pymongo import InsertOne
from DataBaseStuff.MongoengineDocuments.KattiServices.CommonScannerRequest import \
    CommonScannerRequest
from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import DNSExecutionInformation, \
    GSBExecutionInformation
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData
from Scanner.BaseScanner import OOI
from Scanner.DNS.DNSResolver import DomainsForDNSResolverRequest
from CeleryApps.ScanningTasks import dns_scanning_task, gsb_scanning_task, ssl_scanning_task, shodan_api_call_task
from Scanner.GSB.GoogleSafeBrowsing import URLsForGSBRequest
from Scanner.SSLScanner.SSLScanner import DomainsIPsForSSLScanning
from Scanner.Shodan.Shodan import ShodanScanningRequest


class ScannerExecutionRequestBuilder:
    def __init__(self, ownership: Ownership, meta_data: MetaData):
        self._execution_information = None
        self._next_chunk: list[OOI] = []
        self._max_chunk_len = 0
        self._insert_function = None
        self._ownership = ownership
        self._meta_data = meta_data
        self._final_scanner_requests = []
        self._celery_request_cls = None
        self._insert_function = None
        self._additional_execution_information = {}

    def set_execution_information(self, execution_info):
        self._execution_information = execution_info
        match execution_info:
            case DNSExecutionInformation():
                self._max_chunk_len = 2000
                self._celery_task = dns_scanning_task
                self._celery_request_cls = DomainsForDNSResolverRequest
                self._additional_execution_information = {'dig_flags': self._execution_information.dig_flags,
                                                          'dig_type': self._execution_information.dig_type}
            case GSBExecutionInformation():
                self._max_chunk_len = 500
                self._celery_task = gsb_scanning_task
                self._celery_request_cls = URLsForGSBRequest
            case DomainsIPsForSSLScanning():
                self._celery_request_cls = DomainsIPsForSSLScanning
                self._celery_task = ssl_scanning_task
                self._max_chunk_len = 20
            case ShodanScanningRequest():
                self._celery_request_cls = ShodanScanningRequest
                self._celery_task = shodan_api_call_task
                self._max_chunk_len = 20

        return self

    def add_new_ooi(self, new_ooi, force=False):
        self._next_chunk.append(new_ooi)
        if len(self._next_chunk) >= self._max_chunk_len or (force and len(self._next_chunk) > 0):
            self._final_scanner_requests.append(self._build())
            self._next_chunk = []

    def save_final_crawling_request(self):
        CommonScannerRequest()._get_collection().bulk_write(self._final_scanner_requests)
        self._final_scanner_requests = []

    def _build(self) -> CommonScannerRequest | InsertOne:
        new_request = self.build_new_scanner_request()
        dns_celery_signature = self._celery_task.signature(
            args=(self._celery_request_cls(scanner_id=self._execution_information.scanner_id,
                                           ownership_obj=self._ownership,
                                           meta_data_obj=self._meta_data,
                                           time_valid_response=self._execution_information.time_valid_response,
                                           oois=self._next_chunk, **self._additional_execution_information),))
        return self.final_build(new_request=new_request, insert_one=True, celery_signature=dns_celery_signature)

    def build_new_scanner_request(self) -> CommonScannerRequest:
        return CommonScannerRequest(max_lookups=self._execution_information.max_lookups,
                                    priority=self._execution_information.priority,
                                    force=self._execution_information.force,
                                    interval=self._execution_information.interval,
                                    crontab=self._execution_information.cron_tab,
                                    meta_data=self._meta_data,
                                    ownership=self._ownership)

    def final_build(self, celery_signature, new_request, insert_one) -> CommonScannerRequest | InsertOne:
        new_request.celery_task_signature = pickle.dumps(celery_signature)
        if not insert_one:
            new_request.save()
            return new_request
        else:
            return InsertOne(new_request.to_mongo())
