import datetime
import hashlib
import json
import sys
import traceback
from typing import Type
import vt
from pydantic import Field
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.Scanner.VirusTotalConfig import VirusTotalConfig
from DataBaseStuff.MongoengineDocuments.Scanner.VirusTotalScanningRequestResult import VirusTotalScanningRequest, \
    VirusTotalUniversalURLResult, VirusTotalUniversalIPResult, VirusTotalUniversalFileResult, \
    VirusTotalUniversalDomainResult
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject, Config
from Scanner.QuotaMechanic import DayBlockException, MinuteBlockException


@dataclass(config=Config)
class IOCsForVTRequest(BaseScanningRequestForScannerObject):
    endpoint: str = Field(default='urls')
    own_api_key: str | None = None


class VirusTotal(BaseScanner):
    VT_URL_ENDPOINT: str = 'urls'
    VT_IP_ENDPOINT = 'ip_addresses'
    VT_HASH_ENDPOINT = 'files'
    VT_DOMAIN_ENDPOINT = 'domains'

    _scanner_document: VirusTotalConfig
    scanning_request: IOCsForVTRequest

    @property
    def quota_cache_key(self) -> str | None:
        if self.scanning_request.own_api_key:
            return f'{self._scanner_document.id}{hashlib.md5(self.scanning_request.own_api_key.encode()).hexdigest()}'
        return f'{self._scanner_document.id}'

    @property
    def kwargs_for_building_scanning_request(self) -> dict:
        return {'api_endpoint': self.scanning_request.endpoint,
                'own_api_key': self.scanning_request.own_api_key}

    @property
    def result_class(self) -> Type[BaseScanningRequests]:
        return VirusTotalScanningRequest

    @property
    def scanner_mongo_document_class(self):
        return VirusTotalConfig

    @property
    def additional_filter_fields(self) -> dict:
        return {'api_endpoint': self.scanning_request.endpoint}

    def _do_your_scanning_job(self):
        self._vt_client = vt.Client(self._scanner_document.api_key)
        self._get_vt_answer()

    def _get_vt_answer(self):
        match self.scanning_request.endpoint:
            case 'urls':
                ioc = vt.url_id(self.next_ooi_obj.ooi)
            case _:
                ioc = self.next_ooi_obj.ooi
        try:
            response = self._vt_client.get_json("/{}/{}".format(self.scanning_request.endpoint, ioc))['data'][
                'attributes']
            self._hash_answer_string = hashlib.md5(json.dumps(response).encode()).hexdigest()
            self._escape(response)
            self._produce_dates(response)
            self._build_result(response)
        except vt.APIError as e:
            self._logger.debug(f'VT Error {e}')
            if e.code == 'NotFoundError':
                self._build_result(response={'response': 'NotFoundError'})
            elif e.code == 'QuotaExceededError':
                self._ups_quota_failure()

    def _build_result(self, response):
        response.update({'ooi': self.next_ooi_obj.ooi})
        self.scanning_result.api_endpoint = self.scanning_request.endpoint
        match self.scanning_request.endpoint:
            case VirusTotal.VT_URL_ENDPOINT:
                response.update({'vt_id': vt.url_id(self.next_ooi_obj.ooi)})
                self.scanning_result.result = VirusTotalUniversalURLResult.get_result_from_db(
                    filter={'hash_string': self._hash_answer_string},
                    ooi=self.next_ooi_obj.ooi,
                    scanner_obj=self,
                    set_on_insert_dict=response)
            case VirusTotal.VT_IP_ENDPOINT:
                self.scanning_result.result = VirusTotalUniversalIPResult.get_result_from_db(
                    filter={'hash_string': self._hash_answer_string},
                    ooi=self.next_ooi_obj.ooi,
                    scanner_obj=self,
                    set_on_insert_dict=response)
            case VirusTotal.VT_HASH_ENDPOINT:
                self.scanning_result.result = VirusTotalUniversalFileResult.get_result_from_db(
                    filter={'hash_string': self._hash_answer_string},
                    ooi=self.next_ooi_obj.ooi,
                    scanner_obj=self,
                    set_on_insert_dict=response)
            case VirusTotal.VT_DOMAIN_ENDPOINT:
                self.scanning_result.result = VirusTotalUniversalDomainResult.get_result_from_db(
                    filter={'hash_string': self._hash_answer_string},
                    ooi=self.next_ooi_obj.ooi,
                    scanner_obj=self,
                    set_on_insert_dict=response)

    def _escape(self, dic):
        for key in dic:
            if '.' in key:
                dic[key.replace('.', '(punkt)')] = dic[key]
                del dic[key]
                return self._escape(dic)
            if '$' in key:
                dic[key.replace('$', '(dollar)')] = dic[key]
                del dic[key]
                return self._escape(dic)
            for vl in dic.values():
                if isinstance(vl, dict):
                    self._escape(vl)

    def _produce_dates(self, response):
        try:
            if 'first_submission_date' in response:
                response['first_submission_date'] = datetime.datetime.fromtimestamp(response['first_submission_date'])
            if 'last_analysis_date' in response:
                response['last_analysis_date'] = datetime.datetime.fromtimestamp(response['last_analysis_date'])
            if 'last_modification_date' in response:
                response['last_modification_date'] = datetime.datetime.fromtimestamp(response['last_modification_date'])
            if 'last_submission_date' in response:
                response['last_submission_date'] = datetime.datetime.fromtimestamp(response['last_submission_date'])
            self._escape(response)
        except Exception:
            pass

    def _ups_quota_failure(self):
        try:
            vt_quota = self._vt_client.get_json("/{}/{}".format('users', self._scanner_document.api_key))['data']['attributes']['quotas']['api_requests_daily']
        except Exception:
            self._logger.error(traceback.format_exception(*sys.exc_info()))
        else:
            if vt_quota['allowed'] >= vt_quota['used']:
                raise DayBlockException()
            else:
                self.quota.set_minute_block()
                raise MinuteBlockException()
