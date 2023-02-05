import datetime
from typing import Literal

import motor.motor_asyncio
import requests
from bson import ObjectId
from pydantic import BaseModel
from pydantic.generics import GenericModel
from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class DGAFeedRequestModel(FeedGenericRequestModel):
    feed_names: Literal['fkie', '360nl', 'all'] = 'all'
    domains: list[str] | None = None
    families: list[str] | None = None

    def _db_filter(self, attr_name, value, and_filter):
        match attr_name:
            case 'feed_names' if value == 'all':
                and_filter.append({'_cls': {'$in': ['BaseDGAEntry.DGA360FeedEntry', 'BaseDGAEntry.FKIEFeedEntry']}})
            case 'feed_names' if value == 'fkie':
                and_filter.append({'_cls': 'BaseDGAEntry.FKIEFeedEntry'})
            case 'feed_names' if value == '360nl':
                and_filter.append({'_cls': 'BaseDGAEntry.FKIEFeedEntry'})
            case 'domains':
                and_filter.append({'domain': {'$in': self.domains}})
            case 'families':
                and_filter.append({'family': {'$in': self.families}})


class BaseDGAEntry(GenericModel):
    domain: str
    family: str
    start_valid: datetime.datetime
    end_valid: datetime.datetime
    generate: datetime.datetime
    entry_id: str

    @classmethod
    def build_from_db_doc(cls, doc):
        print(doc)
        doc.update({'generate': doc.get('_id').generation_time, 'entry_id': f'{doc.get("_id")}'})
        cls._build(doc)
        return cls(**doc)

    @staticmethod
    def _build(doc):
        raise NotImplementedError

class DGA360Entry(BaseDGAEntry):
    page_link: list[str] | None = None
    comments: str | None = None


class FkieFeedEntry(BaseDGAEntry):
    seed: str = ''

    @staticmethod
    def _build(doc):
        pass


class BambenekEntry(BaseDGAEntry):
    comment: str
    data_name: str


class DGAFeedResponseModel(BaseModel):
    skip: int
    limit: int
    dga_360_entries: list[DGA360Entry] = []
    fkie_entries: list[FkieFeedEntry] = []
    bambenek_entries: list[BambenekEntry] = []



if __name__ == '__main__':
    x = DGAFeedRequestModel(sort='-1',
                            limit=10,
                            feed_names='fkie')

    r = requests.get(url='http://127.0.0.1:8000/api/feed/dga/', data=x.json())
    print(r.content)