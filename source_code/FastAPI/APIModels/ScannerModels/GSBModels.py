from pydantic import HttpUrl, Field
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestWithOneScannerID


class GSBRequest(ScannerGenericRequestWithOneScannerID):
    urls: list[HttpUrl] = Field(max_items=500, min_items=1)