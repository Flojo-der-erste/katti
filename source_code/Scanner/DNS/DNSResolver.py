import subprocess
import sys
import traceback
import typing
from dataclasses import dataclass, field
from ipaddress import ip_address
import jc
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject
from DataBaseStuff.MongoengineDocuments.Scanner.DNSServerConfig import DNSRequest, DNSConfig


@dataclass
class DomainsForDNSResolverRequest(BaseScanningRequestForScannerObject):
    dig_flags: list = field(default_factory=list)
    dig_type: str = 'ANY'


class DNSResolver(BaseScanner):

    _scanner_document: DNSConfig
    scanning_request: DomainsForDNSResolverRequest
    @property
    def result_class(self) -> typing.Union[BaseScannerDocument]:
        return DNSRequest

    @property
    def kwargs_for_building_scanning_request(self) -> dict:
        return {'dig_type': self.scanning_request.dig_type, 'dig_flags': self.scanning_request.dig_flags}

    @property
    def scanner_mongo_document_class(self):
        return DNSConfig

    @property
    def additional_filter_fields(self) -> dict:
        return {'dig_type': self.scanning_request.dig_type,
                'dig_flags': self.scanning_request.dig_flags}

    def _do_your_scanning_job(self):
        cmd_list = ['dig']
        cmd_list.extend(self.scanning_request.dig_flags)
        #raise RetryException()
        for nameserver in self._scanner_document.name_server_ips:
            try:
                if nameserver == '0.0.0.0' and self._scanner_document.dnsbl:
                    ip = ip_address(self.next_ooi_obj.ooi).reverse_pointer.split('.in-addr.arpa')[0]
                    cmd_list.extend([f'{ip}.{self._scanner_document.name_server_dnsbl}', self.scanning_request.dig_type])
                else:
                    cmd_list.extend([f'@{nameserver}', f'{self.next_ooi_obj.ooi}', self.scanning_request.dig_type])
                cmd_output = subprocess.check_output(cmd_list, text=True)
                data = jc.parse('dig', cmd_output)
            except Exception:
                self._logger.exception(f'DIGFAIL: {traceback.format_exception(*sys.exc_info())}')
                query = DNSRequest.DNSQuery(status='DIGFAIL')
            else:
                try:
                    response_data = data[0]
                    if response_data.get('status', '') == 'SERVFAIL':
                        query = DNSRequest.DNSQuery(status='SERVFAIL')
                    else:
                        query = DNSRequest.DNSQuery().build_response(response_data,
                                                                     scanner=self,
                                                                     a_record_evalution=self._scanner_document.a_record_evaluation,
                                                                     aaaa_record_evalution=self._scanner_document.aaaa_record_evaluation,
                                                                     quad9_auth_check=self._scanner_document.quad9_authority_check,
                                                                     ownership=self.scanning_request.get_ownership_obj)
                except Exception:
                    self._logger.exception(f'{traceback.format_exception(*sys.exc_info())}')
                    query = DNSRequest.DNSQuery(status='NOVALIDRESPONSE')
            finally:
                self.scanning_result.query_counter += 1
                query.nameserver_ip = nameserver
                self.scanning_result.queries.append(query)
            if query.status == 'NXDOMAIN' or query.status == 'NOERROR' or query.status == 'NOTIMP' or query.status == 'REFUSED':
                break




