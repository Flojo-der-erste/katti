import ipaddress
from ipaddress import IPv4Address, IPv6Address

from FastAPI.Dependencies import check_domain
from pydantic import validator

from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestWithOneScannerID


class TracerouteRequestModel(ScannerGenericRequestWithOneScannerID):
    domains_or_ips: list[str]

    @validator('domains_or_ips')
    def validate_domains_or_ips(cls, value):
        for v in value:
            try:
                ipaddress.IPv4Address(v)
            except Exception:
                try:
                    ipaddress.IPv6Address(v)
                except:
                    if not check_domain(v):
                        raise ValueError(f'Only valid domains and IPs are allowed.')
        return value


    async def _validate_db_fields(self, db_object):
        pass

    def get_dict_for_celery_request(self) -> dict:
        return {}
