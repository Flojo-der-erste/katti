from fastapi import HTTPException

from FastAPI.Dependencies import FastAPIObjectID
from bson import ObjectId
from pydantic import BaseModel, conint
from pydantic.generics import GenericModel


class GenericScannerResponse(BaseModel):
    results: list[dict] = []

    class Config:
        json_encoders = {
            ObjectId: lambda v: str(v),
        }


class ScannerGenericRequestModel(GenericModel):
    tag_id: FastAPIObjectID | None = ''
    valid_result: conint(ge=0) = 1

    class Config:
        json_encoders = {
            FastAPIObjectID: lambda v: str(v),
        }
    async def _validate_db_fields(self, db_object):
        raise NotImplementedError

    def get_dict_for_celery_request(self) -> dict:
        raise NotImplementedError

    async def validate_db_fields(self, db_object):
        if self.tag_id:
            x = db_object['tags'].find_one({'_id': self.tag_id})
            if not x:
                raise HTTPException(status_code=403, detail='Only valid tag ids.')
        await self._validate_db_fields(db_object)


class ScannerGenericRequestWithOneScannerID(ScannerGenericRequestModel):
    scanner_id: FastAPIObjectID | None

    async def validate_db_fields(self, db_object):
        await super().validate_db_fields(db_object)
        if self.scanner_id:
            result = await db_object['scanner'].find_one({'_id': self.scanner_id, 'active': True})
            if not result:
                raise HTTPException(status_code=404, detail=f'Scanner with ID {self.scanner_id} doesn\'t exists.')
