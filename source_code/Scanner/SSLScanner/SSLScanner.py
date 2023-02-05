import datetime
import json
from typing import Type
from mongoengine.fields import dateutil
from pydantic import Field
from pydantic.dataclasses import dataclass
from sslyze import ServerScanRequest, ServerNetworkLocation, ScanCommand, ServerHostnameCouldNotBeResolved, Scanner, \
    SslyzeOutputAsJson, ServerScanResultAsJson
from DataBaseStuff.MongoengineDocuments.Scanner.SSLScanner import SSLScanResult, TLSResult, SSLScannerDB, \
    CipherSuiteEphemeralKey, CipherSuite, EphemeralKey, Certificatenfo
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests
from Scanner.BaseScanner import BaseScanner, BaseScanningRequestForScannerObject, Config

SSL_SCANNER_ALLOWED_COMMANDS = ['ssl_2_0_cipher_suites',
                                'ssl_3_0_cipher_suites',
                                'tls_1_0_cipher_suites',
                                'tls_1_1_cipher_suites',
                                'tls_1_2_cipher_suites',
                                'tls_1_3_cipher_suites',
                                'tls_compression',
                                'certificate_info',
                                'tls_1_3_early_data']


@dataclass(config=Config)
class DomainsIPsForSSLScanning(BaseScanningRequestForScannerObject):
    port: int = 443
    scan_command_strs: list[str] = Field(default_factory=lambda: SSL_SCANNER_ALLOWED_COMMANDS)

    @property
    def scan_commands_ordered(self) -> list[str]:
        return sorted(self.scan_command_strs, reverse=False)


def build_ciph_ep(result_list):
    ciper_eph = []
    for raw_cipher_suit in result_list:
        new_cipher_eph = CipherSuiteEphemeralKey()
        new_cipher_suit = CipherSuite.get_suite(raw_cipher_suit['cipher_suite'])
        new_cipher_eph.cipher_suite = new_cipher_suit
        if raw_cipher_suit.get('ephemeral_key'):
            new_cipher_eph.ephemeral_key = EphemeralKey(**raw_cipher_suit['ephemeral_key'])
        ciper_eph.append(new_cipher_eph)
    return ciper_eph


class SSLScanner(BaseScanner):
    _db_document: SSLScannerDB
    scanning_request: DomainsIPsForSSLScanning

    @property
    def result_class(self) -> Type[BaseScanningRequests]:
        return SSLScanResult

    @property
    def scanner_mongo_document_class(self):
        return SSLScannerDB

    @property
    def additional_filter_fields(self) -> dict:
        return {'scan_commands': self.scanning_request.scan_commands_ordered, 'port': self.scanning_request.port}

    @property
    def kwargs_for_building_scanning_request(self) -> dict:
        return {'port': self.scanning_request.port, 'scan_commands': self.scanning_request.scan_commands_ordered}

    def _do_your_scanning_job(self):
        location = ServerNetworkLocation(hostname=self.next_ooi_obj.ooi, port=self.scanning_request.port)
        scan_commands = []
        for scan_command_str in self.scanning_request.scan_commands_ordered:
            scan_commands.append(ScanCommand(value=scan_command_str))
        try:
            all_scan_requests = [
                ServerScanRequest(server_location=location, scan_commands=scan_commands),
            ]
        except ServerHostnameCouldNotBeResolved:
            pass
        else:
            start = datetime.datetime.utcnow()
            scanner = Scanner()
            scanner.queue_scans(all_scan_requests)
            stop = datetime.datetime.utcnow()
            json_output = SslyzeOutputAsJson(
                server_scan_results=[ServerScanResultAsJson.from_orm(result) for result in scanner.get_results()],
                date_scans_started=start,
                date_scans_completed=stop,
            )
            out = json_output.json(sort_keys=True, indent=4, ensure_ascii=True)
            json_out = json.loads(out)
            json_out.update(json_out.pop('server_scan_results')[0])
            self._produce_result(json_out)

    def _produce_result(self, json_out):
        scan_results = json_out.pop('scan_result')
        del json_out['sslyze_url']
        del json_out['uuid']
        for key in json_out:
            setattr(self.scanning_result, key, json_out[key])
        if not scan_results:
            return
        scan_results = self._traverse_result(scan_results)
        for result in scan_results:
            help = scan_results[result]
            if help['status'] == 'NOT_SCHEDULED':
                continue
            if help['error_reason']:
                match help['error_reason']:
                    case 'CONNECTIVITY_ISSUE':
                        self.scanning_result.connectivity_error = True
                continue
            match result:
                case 'tls_1_3_cipher_suites' | 'tls_1_2_cipher_suites' | 'tls_1_1_cipher_suites' | 'tls_1_0_cipher_suites' | 'ssl_2_0_cipher_suites':
                    self.scanning_result.tls_ssl_scan_results.append(
                        TLSResult(accepted_cipher_suites=build_ciph_ep(help['result']['accepted_cipher_suites']),
                                  rejected_cipher_suites=build_ciph_ep(help['result']['rejected_cipher_suites']),
                                  tls_version=help['result'].get('tls_version_used'),
                                  error_reason=help.get('error_reason'),
                                  error_trace=help.get('error_trace'),
                                  is_tls_version_supported=help['result'].get('is_tls_version_supported')))
                case 'tls_1_3_early_data':
                    self.scanning_result.tls_ssl_scan_results.append(TLSResult(error_reason=help.get('error_reason'),
                                                                               error_trace=help.get('error_trace'),
                                                                               tls_1_3_early_data=help.get('result')))
                case 'tls_compression':
                    self.scanning_result.tls_ssl_scan_results.append(TLSResult(error_reason=help.get('error_reason'),
                                                                               error_trace=help.get('error_trace'),
                                                                               supports_compression=help.get('result')))
                case 'certificate_info':
                    self.scanning_result.certificate_info = Certificatenfo.get_certificate_info(help.get('result').get('certificate_deployments'), self.next_ooi_obj.ooi)

    def _traverse_result(self, value, key=""):
            if isinstance(value, dict):
                return {key: self._traverse_result(value, key) for key, value in value.items()}
            elif isinstance(value, list):
                return [self._traverse_result(item) for item in value]
            match key:
                case 'serial':
                    return {'as_hex': hex(value), 'as_str': str(value)}
                case "timestamp" | "issued" | "expires" | "last_update":
                    return dateutil.parser.parse(value)
                case _ if isinstance(value, int) and value > 9223372036854775807:
                    return str(value)
                case _:
                    return value