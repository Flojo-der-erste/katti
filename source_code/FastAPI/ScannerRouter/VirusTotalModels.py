from typing import Literal
from pydantic import BaseModel, Field
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestWithOneScannerID
from Scanner.VirusTotal.VirusTotal import VirusTotal
from pydantic import BaseModel


class VirusTotalRequest(ScannerGenericRequestWithOneScannerID):
    vt_endpoint: Literal[VirusTotal.VT_URL_ENDPOINT, VirusTotal.VT_IP_ENDPOINT, VirusTotal.VT_DOMAIN_ENDPOINT, VirusTotal.VT_HASH_ENDPOINT]
    oois: list[str] = Field(max_items=20, min_items=1)

    async def _validate_db_fields(self, db_object):
        pass

    def get_dict_for_celery_request(self) -> dict:
        return {}

class EndpointResponse(BaseModel):
    endpoints: list[str] = [VirusTotal.VT_URL_ENDPOINT, VirusTotal.VT_IP_ENDPOINT, VirusTotal.VT_DOMAIN_ENDPOINT, VirusTotal.VT_HASH_ENDPOINT]