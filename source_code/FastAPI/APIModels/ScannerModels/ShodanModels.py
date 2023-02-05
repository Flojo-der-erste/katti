from ipaddress import IPv4Address, IPv6Address
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestWithOneScannerID


class ShodanAPIExecuteRequest(ScannerGenericRequestWithOneScannerID):
    host_ips = list[IPv4Address, IPv6Address]

    async def _validate_db_fields(self, db_object):
        pass

    def get_dict_for_celery_request(self) -> dict:
        pass
