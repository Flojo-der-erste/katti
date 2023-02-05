import datetime
import json
import sys
import traceback
from typing import Type, Literal
import requests
from Scanner.DNS.rdata_parser_functions import parse_a_record, parse_soa_record
from pydantic import Field
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject, Config, OOI
from DataBaseStuff.MongoengineDocuments.Scanner.FarsightDocument import FarsightDocument, FarsightQuerryResult, FarsightRequest

FARSIGHT_FIRST_PART_OF_URL = 'https://api.dnsdb.info/dnsdb/v2/lookup/'
FARSIGHT_ALLOWED_RECORD_TYPES = ['ANY']

@dataclass
class FarsightOOI(OOI):
    raw_query: bool = False
    _ooi = None

    @property
    def ooi(self):
        if self._ooi:
            return self._ooi
        if not self.raw_query:
            self._ooi = self.raw_ooi
        if self.raw_query:
            self._ooi = self.raw_ooi.split(FARSIGHT_FIRST_PART_OF_URL)[1].split('/')[2]
        return self._ooi


@dataclass(config=Config)
class FarsightQuerries(BaseScanningRequestForScannerObject):
    oois: list[FarsightOOI] = Field(default_factory=list)
    raw_query: bool = False
    record_type: str = 'ANY'
    rdata_or_rrset: Literal['rdata_name', 'rdata_ip', 'rrset'] = 'rrset'
    time_last_after: int | None = None
    time_first_before: int | None = None
    bailiwick: str | None = None
    limit: int = Field(default=5000, gt=0, lt=30000)

    def get_url_for_ooi(self, next_ooi: FarsightOOI):
        if next_ooi.raw_query:
            return next_ooi.raw_ooi
        else:
            match self.rdata_or_rrset:
                case 'rrset':
                    second_part_str = f'rrset/name/{next_ooi.ooi}/{self.record_type}{("/"+self.bailiwick) if self.bailiwick else ""}?limit={self.limit}'
                case 'rdata_name':
                    second_part_str = f'rdata/name/{next_ooi.ooi}'
                case 'rdata_ip':
                    second_part_str = f'rdata/name/{next_ooi.ooi}'
                case _:
                    raise Exception()
            second_part_str += f'&time_last_after={self.time_last_after}' if self.time_last_after else ""
            second_part_str += f'&time_first_before={self.time_first_before}' if self.time_first_before else ""
            return f'{FARSIGHT_FIRST_PART_OF_URL}{second_part_str}'

    def _own_post_init(self):
        pass


class Farsight(BaseScanner):
    scanning_request: FarsightQuerries
    _scanner_document: FarsightDocument

    @property
    def result_class(self) -> Type[BaseScanningRequests]:
        return FarsightRequest

    @property
    def scanner_mongo_document_class(self):
        return FarsightDocument


    @property
    def additional_filter_fields(self) -> dict:
        return {'url': self.scanning_request.get_url_for_ooi(self.next_ooi_obj)}

    def _do_your_scanning_job(self):
        url = self.scanning_request.get_url_for_ooi(self.next_ooi_obj)
        self.scanning_result.url = url
        try:
            farsight_response = requests.get(url, headers={'X-API-KEY': self._scanner_document.api_key})
            if not farsight_response.status_code == 200:
                raise Exception(f'Bad statuscode {farsight_response.status_code}, url: {url}')
        except Exception:
            self._logger.exception(f'Farsight fail: {traceback.format_exception(*sys.exc_info())}')
            raise
        else:
            for line in farsight_response.content.decode('utf-8').splitlines():
                json_line = json.loads(line)
                if 'cond' in json_line:
                    continue
                result_json = json_line['obj']
                self.scanning_result.result_counter += 1
                self.scanning_result.farsight_querry_results.append(self._save_querry_result(result_json))

    def _save_querry_result(self, result_json):
        match result_json['rrtype']:
            case 'A':
                record_dict = parse_a_record(rdata=result_json['rdata'][0])
            case 'NS':
                record_dict = {'name_servers': result_json['rdata']}
            case 'SOA':
                record_dict = parse_soa_record(rdata=result_json['rdata'][0])
            case _:
                record_dict = {'rdata': result_json['rdata']}
        return FarsightQuerryResult.get_result_from_db(filter={'ooi': result_json['rrname'],
                                                               'time_first': datetime.datetime.fromtimestamp(result_json['time_first']),
                                                               'type': result_json['rrtype'],
                                                               'bailiwick': result_json.get('bailiwick'),
                                                                'record': record_dict},
                                                       ooi=None,
                                                       scanner_obj=self,
                                                       update={'$max': {'time_last': datetime.datetime.fromtimestamp(result_json['time_last']), 'count': result_json['count']}})
