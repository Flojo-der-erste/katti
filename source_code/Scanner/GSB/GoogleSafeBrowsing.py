import json
import sys
import traceback
import requests
from pydantic.dataclasses import dataclass
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject, Config
from DataBaseStuff.MongoengineDocuments.Scanner.GoogleSafeBrwosingConfig import GSbRequest, GoogleSafeBrowserConfig, GSBFindings


@dataclass(config=Config)
class URLsForGSBRequest(BaseScanningRequestForScannerObject):
    pass


class GoogleSafeBrowsing(BaseScanner):
    _scanner_document: GoogleSafeBrowserConfig
    def _build_threat_info(self, url):
        ti = {}
        ti.update({'threatInfo':{'threatTypes': self._scanner_document.threat_types,
                   'platformTypes': self._scanner_document.platform_types,
                   'threatEntryTypes': ['URL'],
                   'threatEntries': [{'url': url}]}})
        return ti

    @property
    def result_class(self):
        return GSbRequest

    @property
    def scanner_mongo_document_class(self):
        return GoogleSafeBrowserConfig

    def _do_your_scanning_job(self):
        headers = {'content-type': 'application/json'}
        try:
            response = requests.post(url=f'http://{self._scanner_document.gsb_server_ip}:{self._scanner_document.gsb_server_port}/v4/threatMatches:find', data=json.dumps(self._build_threat_info(self.next_ooi_obj.ooi)),
                                     headers=headers)
        except Exception:
            self._logger.error(f'{self.next_ooi_obj.ooi}\n {traceback.format_exception(*sys.exc_info())}')
            self._scanning_result = None
        else:
            self._produce_response(response.content)

    def _produce_response(self, response_content):
        self._logger.debug('Produce response')
        try:
            content = json.loads(response_content.decode('utf-8'))
        except Exception:
            self._logger.error(f'{self.next_ooi_obj.ooi}\n {traceback.format_exception(*sys.exc_info())}')
            self._scanning_result = None
        else:
                findings = []
                if 'matches' in content:
                    for result in content['matches']:
                        findings.append(GSBFindings.Findings(platformType=result['platformType'], threatType=result['threatType']).to_mongo())
                self.scanning_result.findings = GSBFindings.get_result_from_db(filter={'url': self.next_ooi_obj.ooi, 'findings': findings},
                                                                               ooi=None,
                                                                               scanner_obj=self,
                                                                               set_on_insert_dict={'finding_counter': len(findings)})
                self.scanning_result.finding_counter = len(findings)

