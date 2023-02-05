from pydantic import BaseModel

from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class RSSFeedModel(FeedGenericRequestModel):
    url: list[str] | None = None
    title: list[str] | None = None

    rss_feed_name: list[str] | None = None


class RSSFeedEntry(BaseModel):
    url: str
    title: str
    summary: str

class RSSFeedResponseModel(BaseModel):
    skip: int
    limit: int
    feed_name: str
    entries: list[RSSFeedEntry]