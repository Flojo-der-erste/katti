from pydantic import validator, Field
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestModel, \
    ScannerGenericRequestWithOneScannerID
from FastAPI.Dependencies import check_domain
from Scanner.SSLScanner.SSLScanner import SSL_SCANNER_ALLOWED_COMMANDS


class SSLScannerRequest(ScannerGenericRequestWithOneScannerID):
    domains: list[str] = Field(max_items=10, min_items=1)
    port: int = 443

    ssl_2_0_cipher_suites: bool = True
    ssl_3_0_cipher_suites: bool = True
    tls_1_0_cipher_suites: bool = True
    tls_1_1_cipher_suites: bool = True
    tls_1_2_cipher_suites: bool = True
    tls_1_3_cipher_suites: bool = True
    tls_compression: bool = True
    tls_1_3_early_data: bool = True
    certificate_info: bool = True

    def get_dict_for_celery_request(self) -> dict:
        return {'scan_command_strs': self.get_scan_cmd_str_list}

    @property
    def get_scan_cmd_str_list(self) -> list[str]:
        cmds = []
        for possible_cmd in SSL_SCANNER_ALLOWED_COMMANDS:
            if getattr(self, possible_cmd):
                cmds.append(possible_cmd)
        return cmds

    @validator('domains')
    def validate_domain(cls, v: list[str]):
        for domain in v:
            if not check_domain(domain):
                raise ValueError(f'Onl valid domains are allowed. {domain}')
        return v

    async def _validate_db_fields(self, db_object):
        pass
