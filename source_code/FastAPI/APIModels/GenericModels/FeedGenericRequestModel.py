import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, conint, HttpUrl
from pydantic.generics import GenericModel


class FeedGenericRequestModel(GenericModel):
    time_start: datetime.datetime | None = None
    time_end: datetime.datetime | None = None
    valid_or_insert: Literal['valid', 'insert'] = 'valid'
    sort: Literal['1', '-1'] = 1
    skip: conint(gt=-1) = 0
    limit: conint(gt=-1, lt=1001) = 1000
    ids: list[str] = []
    tag: str | None = None

    #  and_or: bool | None = False


    def db_filter(self):
        self_dict = self.__dict__
        and_filter = []
        for attr in self_dict:
            value = self_dict[attr]
            if not value:
                continue
            match attr:
                case 'ids' if len(self.ids) > 0:
                    x = [ObjectId(id) for id in self.ids]
                    and_filter.append({'_id': {'$in': x}})
                case 'skip' | 'limit':
                    continue
                case 'time_start':
                    match self.valid_or_insert:
                        case 'valid':
                            and_filter.append({'start_valid': {'$lte': self.time_start}})
                        case 'insert':
                            and_filter.append({'_id': {'$lte': ObjectId.from_datetime(self.time_start)}})
                case 'time_end':
                    match self.valid_or_insert:
                        case 'valid':
                            and_filter.append({'start_valid': {'$gte': self.time_start}})
                        case 'insert':
                            and_filter.append({'_id': {'$gte': ObjectId.from_datetime(self.time_start)}})
                case 'tag':
                    pass
                case _:
                    self._db_filter(attr, value, and_filter)

        return [{'$match': {'$and': and_filter}},
                {'$sort': {'_id':int(self.sort)}},
                {'$skip': self.skip},
                {'$limit': self.limit}]


    def _db_filter(self, attr_name, value, and_filter):
        raise NotImplementedError
