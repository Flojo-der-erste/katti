import datetime
import time
from random import randint
from mongoengine import IntField, DateTimeField, BooleanField,EmbeddedDocument
from RedisCacheLayer.RedisMongoCache import set_up_connection


class MongoDBQuota(EmbeddedDocument):
    max_minute_quota = IntField()
    max_day_quota = IntField()
    max_month_quota = IntField()

    day_release = BooleanField(default=False)
    month_release = BooleanField(default=False)

    blocked = BooleanField(default=False)
    last_blocked = DateTimeField()


class MinuteBlockException(Exception):
    def __str__(self) -> str:
        return 'MinuteBlock'

class DayBlockException(Exception):

    def __str__(self) -> str:
        return 'DayBlock'


class QMinute(MinuteBlockException):
    pass


class QDay(DayBlockException):
    pass


class QuotaMechanic:
    def __init__(self, cache_key):
        self._redis = set_up_connection()
        self._cache_key: str = cache_key

    def check_minute_block(self):
        if not self._redis.get(f'quota_{datetime.datetime.utcnow().strftime("%m %d %Y %H:%M")}_{self._cache_key}'):
            return True
        else:
            return False

    def check_day_block(self):
        if not self._redis.get(f'quota_{datetime.datetime.utcnow().strftime("%m %d %Y")}_{self._cache_key}'):
            return True
        else:
            raise QDay()

    def set_minute_block(self):
        self._redis.set(name=f'quota_{datetime.datetime.utcnow().strftime("%m %d %Y %H:%M")}_{self._cache_key}',
                        value=f'{datetime.datetime.utcnow().strftime("%m %d %Y %H:%M:%S")}',
                        ex=60)

    def set_day_block(self):
        day_hours_left = (24 - datetime.datetime.utcnow().hour)
        self._redis.set(name=f'quota_{datetime.datetime.utcnow().strftime("%m %d %Y")}_{self._cache_key}',
                        value=f'{datetime.datetime.utcnow().strftime("%m %d %Y %H:%M:%S")}',
                        ex=(day_hours_left + 2)*60*60)

    def check_and_wait_minute_block(self, retries=3, start_bool=30, end_bool=90):
        counter = 1
        while counter <= retries:
            if self.check_minute_block():
                return
            time.sleep(randint(a=start_bool, b=end_bool))
            counter += 1
        raise QMinute()

