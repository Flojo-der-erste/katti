from pydantic import BaseModel

from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class TorFeedModel(FeedGenericRequestModel):
    node: str | None = None


class TorFeedEntry(BaseModel):
    test: str | None = 'test'


class TorFeedResponseModel(BaseModel):
    skip: int
    limit: int
    entries: list[TorFeedEntry]