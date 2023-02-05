from fastapi import HTTPException
from pydantic import validator, Field

from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestModel
from FastAPI.Dependencies import FastAPIObjectID, check_domain
from Scanner.SSLScanner.SSLScanner import SSL_SCANNER_ALLOWED_COMMANDS


class SSLScannerRequest(ScannerGenericRequestModel):
    ssl_scanner_id: FastAPIObjectID
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
        try:
            result = await db_object['scanner'].find_one({'_id': self.ssl_scanner_id})
        except Exception:
            raise HTTPException(status_code=403, detail='Upps.')
        else:
            if not result:
                raise HTTPException(status_code=404, detail='Please check your request.')
