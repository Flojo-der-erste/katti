from typing import List
from pydantic import BaseModel
from FastAPI.APIModels.GenericModels.ScannerGenericRequestModels import ScannerGenericRequestModel


class IBMXForceRequestModel(ScannerGenericRequestModel):
    ooi: List[str]


class IBMXForceResults(BaseModel):
    raw_result: dict
    ooi: str


class IBMXForceResponseModel(ScannerGenericRequestModel):
    results: List[IBMXForceResults] = []