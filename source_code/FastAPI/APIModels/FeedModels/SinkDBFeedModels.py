from pydantic import BaseModel

from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class SinkDBFeed(FeedGenericRequestModel):
    node: str | None = None


class SinkDBFeedEntry(BaseModel):
    test: str | None = 'test'


class SinkDBResponseModel(BaseModel):
    skip: int
    limit: int
    entries: list[SinkDBFeedEntry]