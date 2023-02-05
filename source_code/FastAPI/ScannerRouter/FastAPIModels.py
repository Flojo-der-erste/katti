from ipaddress import IPv4Address, IPv6Address

from fastapi import HTTPException
from pydantic import Field, validator, HttpUrl
from pydantic.typing import Literal

from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestModel
from FastAPI.Dependencies import check_domain, FastAPIObjectID, db
from Scanner.Farsight.Farsight import FARSIGHT_ALLOWED_RECORD_TYPES, FARSIGHT_FIRST_PART_OF_URL


class FrasightRequestQuery(ScannerGenericRequestModel):
    raw_querries: list[HttpUrl] = Field(min_items=1, max_items=20, default_factory=list)
    scanner_id: FastAPIObjectID | None = None

    @validator('raw_querries')
    def validate_raw_query(cls, value):
        for query in value:
            if not FARSIGHT_FIRST_PART_OF_URL in query:
                raise ValueError(f'Only valid farsight querries are allowed. {query}')
        return value

    @staticmethod
    def get_ooi_from_query(query):
        return query.split(FARSIGHT_FIRST_PART_OF_URL)[1].split('/')[2]

    async def _validate_db_fields(self, db_object):
        pass

    def get_dict_for_celery_request(self) -> dict:
        return {}


class FarsightRequestRawRequest(ScannerGenericRequestModel):

    oois: list[str] = Field(default=['bsi.de'], max_items=20, min_items=1)
    record_type: str | None = 'ANY'
    rdata_or_rrset: Literal['rdata_name', 'rdata_ip', 'rrset'] = 'rrset'

    time_last_after: int | None = 0
    time_first_before: int | None = 0
    bailiwick: str | None = ''
    limit: int = Field(default=5000, gt=0, lt=30000)
    scanner_id: FastAPIObjectID | None = None

    async def _validate_db_fields(self, db_object):
        if self.scanner_id:
            x = await db['scanner'].find_one({'_id': self.scanner_id, 'active': True})
            if not x:
                raise HTTPException(status_code=501, detail=f'Scanner {self.scanner_id} not available')

    @validator('bailiwick')
    def validate_bailiwick(cls, value):
        if value == '':
            return None

    @validator('record_type')
    def validate_record_type(cls, value):
        if value not in FARSIGHT_ALLOWED_RECORD_TYPES:
            raise ValueError(f'Not allowed record type: {value}.')
        return value

    @validator('rdata_or_rrset')
    def validate_rdata_or_rrset(cls, value, values, **kwargs):
        if value == 'rdata_ip':
            for ooi in values['oois']:
                if not FarsightRequestRawRequest.is_ooi_ip(ooi):
                    raise ValueError(f'Only valid IPv4 or IPv6 are allowed. {values["oois"]}')
        if value == 'rrset' or value == 'rdata_name':
            try:
                for ooi in values['oois']:
                    check_domain(ooi)
            except Exception:
                raise ValueError(f'Only valid domains are allowed. {values["oois"]}')
        return value

    @staticmethod
    def is_ooi_ip(ooi) -> bool:
        try:
            IPv4Address(ooi)
        except Exception:
            try:
                IPv6Address(ooi)
            except Exception:
                pass
            else:
                return True
        else:
            return True
        return False

    def get_dict_for_celery_request(self) -> dict:
        return {'record_type': self.record_type,
                'rdata_or_rrset': self.rdata_or_rrset,
                'time_last_after': self.time_last_after,
                'time_first_before': self.time_first_before,
                'bailiwick': self.bailiwick,
                'limit': self.limit}


