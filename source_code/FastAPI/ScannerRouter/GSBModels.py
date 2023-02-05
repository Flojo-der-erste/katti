from pydantic import HttpUrl, Field
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestWithOneScannerID


class GSBRequest(ScannerGenericRequestWithOneScannerID):
    urls: list[HttpUrl] = Field(max_items=500, min_items=1)

    async def _validate_db_fields(self, db_object):
        pass

    def get_dict_for_celery_request(self) -> dict:
        return {}

