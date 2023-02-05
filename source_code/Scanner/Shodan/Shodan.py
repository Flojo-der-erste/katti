import hashlib
import json
from typing import Type
from mongoengine.fields import dateutil
import shodan
from shodan import APIError
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.Scanner.Shodan import ShodanScannerDB, ShodanScanRequest, traverse_result, \
    ShodanCrawlerResult, ShodanMeta
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject, Config


@dataclass(config=Config)
class ShodanScanningRequest(BaseScanningRequestForScannerObject):
    pass


class ShodanScanner(BaseScanner):
    scanning_request: BaseScanningRequestForScannerObject
    _scanner_document: ShodanScannerDB

    @property
    def result_class(self) -> Type[BaseScanningRequests]:
        return ShodanScanRequest

    @property
    def scanner_mongo_document_class(self):
        return ShodanScannerDB

    def _do_your_scanning_job(self):
        try:
            res = shodan.Shodan(self._scanner_document.api_key).host(self.next_ooi_obj.ooi)
        except APIError as e:
            self.scanning_result.api_error = f'{e}'
        else:
            crawler_results = res.pop('data')
            self.scanning_result.shodan_last_update = dateutil.parser.parse(res['last_update'])
            self._build_shodan_meta(res)
            self._build_crawler_results(crawler_results)

    def _build_shodan_meta(self, shodan_meta):
        hash_str = hashlib.md5(json.dumps(shodan_meta).encode()).hexdigest()
        set_on_insert_dict = traverse_result(shodan_meta)
        self.scanning_result.shodan_meta = ShodanMeta.get_result_from_db(filter={'hash_str': hash_str},
                                                                         scanner_obj=self,
                                                                         ooi=self.next_ooi_obj.ooi,
                                                                         set_on_insert_dict=set_on_insert_dict)

    def _build_crawler_results(self, crawler_results):
        for crawler_result in sorted(crawler_results, key=lambda x: x['timestamp']):
            hash_str = hashlib.md5(json.dumps(crawler_result).encode()).hexdigest()
            set_on_insert_dict = traverse_result(crawler_result)
            self.scanning_result.crawler_results.append(ShodanCrawlerResult.get_result_from_db(filter={'hash_str': hash_str},
                                                                                               scanner_obj=self,
                                                                                               ooi=self.next_ooi_obj.ooi,
                                                                                               set_on_insert_dict=set_on_insert_dict))

    def handle_quota_block(self, exception: Exception):
        pass

