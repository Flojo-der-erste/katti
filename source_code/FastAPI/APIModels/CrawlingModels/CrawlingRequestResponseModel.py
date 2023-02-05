from pydantic import BaseModel


class CrawlingRequestModel(BaseModel):
    src_ips: list[str] | None = None
    src_ports: list[str] | None = None

    dst_ips: list[str] | None = None
    dst_ports: list[str] | None = None

    malware_cats: list[str] | None = None



class CrawlingRequestResponseModel(BaseModel):
    skip: int
    limit: int
    rest: dict