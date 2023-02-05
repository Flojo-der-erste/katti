from typing import List
from pydantic import BaseModel
from FastAPI.APIModels.GenericModels.ScannerGenericRequestModels import ScannerGenericRequestModel


class VirusTotalRequestModel(ScannerGenericRequestModel):
    ooi: List[str]


class VirusTotalResults(BaseModel):
    raw_result: dict
    ooi: str


class VirusTotalResponseModel(ScannerGenericRequestModel):
    results: List[VirusTotalResults] = []