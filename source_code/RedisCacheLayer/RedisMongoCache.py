import pickle
import motor.motor_asyncio
import redis
from pydantic import Field
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.Crawling.HTTPRequestHeader import HTTPRequestHeader, RegexHTTPRequestHeader
from Utils.ConfigurationClass import DatabaseConfigs
from bson import ObjectId
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle
from Utils.pydanticStuff import PydanticConfig

REDIS_CONNECTION: redis.Redis | None = None


@dataclass(config=PydanticConfig)
class ManualConnectionSettings:
    host: str
    port: int
    password: str
    user: str | None = None


@dataclass(config=PydanticConfig)
class URLHeadersRedisCache:
    header_fields_all: list[HTTPRequestHeader] = Field(default_factory=list)
    header_fields_regex: list[RegexHTTPRequestHeader] = Field(default_factory=list)


def set_up_connection(manual: ManualConnectionSettings | None = None) -> redis.Redis:
    global REDIS_CONNECTION
    if not REDIS_CONNECTION:
        x = manual if manual else DatabaseConfigs.get_config().redis
        REDIS_CONNECTION = redis.Redis(host=x.host, username=x.user if not x == '' else None, port=x.port, password=x.password)
    return REDIS_CONNECTION


class CacheFailure(Exception):
    pass


class RedisMongoCache:
    def __init__(self, manual_con_data: ManualConnectionSettings = None):
        self._connection = set_up_connection(manual=manual_con_data)
        self._redis_lock = None

    @property
    def redis_connection(self):
        return REDIS_CONNECTION

    def set_stop_signal(self, signal_id: str, set=True):
        self.insert_value_pair(key=f'stop_signal_{signal_id}', value=str(set))

    def is_stop_signal_set(self, signal_id: str):
        if not self.get_value(f'stop_signal_{signal_id}'):
            return False
        return True

    def delete(self, key):
        self._connection.delete(key)

    def get_value(self, key: str):
        return self._connection.get(key)

    def insert_value_pair(self, key, value, ttl: int=0):
        if ttl <= 0:
            self._connection.set(key, value)
        else:
            self._connection.set(key, value, ex=ttl)

    def setnx_value_pair(self, key, value):
        return self._connection.setnx(key, value)

    def spider_mode_cache(self, url, crawling_request_id: ObjectId) -> ObjectId | None:
        cache_entry = self.get_value(f'spider_mode:{url}_{crawling_request_id}')
        if not cache_entry:
            try:
                cache_entry = Bundle.objects.get(url__url=url, meta_data__crawling_request_id=crawling_request_id).only('id')
                self.insert_value_pair(key=f'spider_mode:{url}_{crawling_request_id}', value=f'{cache_entry.id}')
            except Exception:
                return None
        return ObjectId(cache_entry)

    def get_mongoengine_cache(self, cache_key: str, mongoengine_cls, mongo_filter=None, ttl=10*60):
        try:
            object_SON = self.get_value(key=cache_key)
            if object_SON:
                x = mongoengine_cls._from_son(pickle.loads(object_SON))
                return x
            if mongo_filter:
                x = mongoengine_cls.objects.get(**mongo_filter)
                self.insert_value_pair(key=cache_key, value=pickle.dumps(x.to_mongo()), ttl=ttl)
                return x
        except Exception as e:
            raise CacheFailure(e)

    async def get_mongoengine_cache_async(self, mongo_motor: motor.motor_asyncio.AsyncIOMotorClient, cache_key: str, mongoengine_cls, mongo_filter=None, ttl= 10*60):
        try:
            object_SON = self.get_value(key=cache_key)
            if object_SON:
                return mongoengine_cls._from_son(pickle.loads(object_SON))
            if mongo_filter:
                x = mongo_motor[mongoengine_cls()._get_collection()].find_one(mongo_filter)
                if not x:
                    return None
                self.insert_value_pair(key=cache_key, value=pickle.dumps(x.to_mongo()), ttl=ttl)
                return x
        except Exception as e:
            raise CacheFailure(e)

    def set_mongoengine_object(self, mongoengine_object, cache_key, ttl=180):
        self.insert_value_pair(key=cache_key, value=pickle.dumps(mongoengine_object.to_mongo()), ttl=ttl)

    def save_mongoengine_object_and_set_cache(self, mongoengine_obj, cache_key, ttl=0):
        mongoengine_obj.save()
        self.set_mongoengine_object(mongoengine_obj, cache_key, ttl)

    def insert_http_headers_for_crawling(self, headers_cache: URLHeadersRedisCache, bundle_id: ObjectId):
        self.insert_value_pair(key=f'header_cache_{bundle_id}', value=pickle.dumps(headers_cache))

    def get_http_headers_for_crawling(self, bundle_id: ObjectId) -> URLHeadersRedisCache | None:
        x = self.get_value(f'header_cache_{bundle_id}')
        if x:
            x = pickle.loads(x)
        return x


