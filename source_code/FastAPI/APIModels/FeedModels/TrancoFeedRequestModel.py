import datetime
from typing import List

from pydantic import BaseModel
from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class TrancoFeedRequestModel(FeedGenericRequestModel):
    domain: List[str] | None = None
    rank: List[int] | None = None

    def _db_filter(self, attr_name, value, filter_array) -> bool:
        pass

    def test(self):
        print(self.__dict__)


class TrancoFeedEntry(BaseModel):
    domain: str
    rank: int
    start_valid: datetime.datetime
    end_valid: datetime.datetime


class TrancoFeedResponseModel(BaseModel):
    skip: int
    limit: int
    entries: List[TrancoFeedEntry]