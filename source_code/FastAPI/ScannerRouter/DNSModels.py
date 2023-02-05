import ipaddress
from fastapi import HTTPException
from pydantic import BaseModel, validator, Field
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import ScannerGenericRequestModel
from FastAPI.Dependencies import FastAPIObjectID, check_domain


class DNSScanner(BaseModel):
    name: str
    id: FastAPIObjectID
    allowed_dns_records: list[str]
    name_server_ips: list[str]
    quad9_authority_check: bool
    time_valid_response: int
    aaaa_record_evaluation: dict | None
    a_record_evaluation: dict | None

    @classmethod
    def build_from_raw_db_answer(cls, raw_db_answer: dict):
        raw_db_answer['id'] = f'{raw_db_answer.pop("_id")}'
        return cls(**raw_db_answer)


class DNSScannerBaseRequest(ScannerGenericRequestModel):
    dns_scanner_ids: list[FastAPIObjectID] = Field(max_items=20, min_items=0, default_factory=list)
    record_type: str = 'ANY'

    async def _validate_db_fields(self, db_object):
        find_dict = {'_id': {'$in': self.dns_scanner_ids},
                     'allowed_record_types': self.record_type,
                     'active': True}
        if isinstance(self, IPCheckDNSRequest):
            find_dict.update({'dnsbl': True})
        try:
            result_list = [x async for x in db_object['scanner'].find(find_dict)]

        except Exception as e:
            raise HTTPException(status_code=403, detail='Upps.')
        else:
            if not len(result_list) == len(self.dns_scanner_ids):
                raise HTTPException(status_code=404, detail='Please check your request.')

    def get_dict_for_celery_request(self) -> dict:
        if isinstance(self, IPCheckDNSRequest):
            return {'dig_type': self.record_type, 'dig_flags': []}
        else:
            return {'dig_type': self.record_type, 'dig_flags': []}


class DNSScannerRequest(DNSScannerBaseRequest):
    domains: list[str] = Field(max_items=50, min_items=1, default_factory=list)
    dig_flags: list[str] = []

    @validator('domains')
    def validate_domains(cls, value):
        for domain in value:
            if not check_domain(domain):
                raise ValueError(f'Only valid domains are allowed. {domain}')
        return value


class IPCheckDNSRequest(DNSScannerBaseRequest):
    ipv4: list[ipaddress.IPv4Address]


class SingleDNSResults(BaseModel):
    dns_scanner_id: FastAPIObjectID
    result: dict
