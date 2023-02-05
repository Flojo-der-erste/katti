from pydantic import BaseModel

from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class BitsightFeedRequestModel(FeedGenericRequestModel):
    src_ips: list[str] | None = None
    src_ports: list[str] | None = None

    dst_ips: list[str] | None = None
    dst_ports: list[str] | None = None

    malware_cats: list[str] | None = None



class BitsightFeedResponseModel(BaseModel):
    skip: int
    limit: int
    rest: dict