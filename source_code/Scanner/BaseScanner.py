import datetime
import hashlib
import logging
import sys
import time
import traceback
import typing
from dataclasses import InitVar, field
from pydantic import Field
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData, Ownership
from Scanner.QuotaMechanic import QuotaMechanic, MinuteBlockException, DayBlockException, QMinute, QDay
import redis_lock
from bson import ObjectId, SON
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests


class NotValidOOIException(Exception):
    pass


class Config:
    arbitrary_types_allowed = True


@dataclass
class OOI:
    raw_ooi: typing.Any
    meta_data_as_son: SON | None = field(init=False, default=None)
    meta_data_obj: InitVar[MetaData] = None

    def __post_init__(self, meta_data_obj):
        if meta_data_obj:
            self.meta_data_as_son = meta_data_obj.to_mongo()

    @property
    def ooi(self):
        return str(self.raw_ooi)


@dataclass(config=Config)
class BaseScanningRequestForScannerObject:
    scanner_id: ObjectId
    ownership_obj: InitVar[Ownership]
    meta_data_obj: InitVar[MetaData] = None
    ownership_as_son: SON = Field(init=False, default=None)
    meta_data_as_son: SON | None = Field(init=False, default=None)

    time_valid_response: int = Field(qe=0, default=3600)
    oois: list[OOI] = Field(default_factory=list)

    def __post_init__(self, ownership_obj, meta_data_obj):
        if meta_data_obj:
            self.meta_data_as_son = meta_data_obj.to_mongo()
        self.ownership_as_son = ownership_obj.to_mongo()
        self._own_post_init()

    def _own_post_init(self):
        pass

    @property
    def get_ownership_obj(self) -> Ownership:
        return Ownership._from_son(self.ownership_as_son)

    @property
    def next_ooi_obj(self):
        return self.oois.pop(0) if len(self.oois) > 0 else None

    @property
    def ooi_count(self) -> int:
        return len(self.oois)

    @property
    def force(self) ->bool:
        if self.time_valid_response <= 0:
            return True
        return False



class ExtremFailure(Exception):
    pass


class RetryException(Exception):
    pass


class BaseScanner:
    def __init__(self, logger, scanning_request: typing.Union[BaseScanningRequestForScannerObject] = None):
        self._scanner_document: typing.Union[BaseScannerDocument] | None = None
        self._logger = logger
        self.scanning_request: typing.Union[BaseScanningRequestForScannerObject] | None = scanning_request
        self._redis_cache = RedisMongoCache()
        self.scanning_result = None
        self._redis_lock: redis_lock.Lock | None = None
        self.next_ooi_obj: typing.Type[OOI] | None = None
        self.api_usage_stats = None

        self.quota: QuotaMechanic | None = None

        logging.getLogger("redis_lock.thread").disabled = True
        logging.getLogger("redis_lock").disabled = True

    @property
    def result_class(self) -> typing.Type[BaseScanningRequests]:
        raise NotImplementedError

    @property
    def quota_cache_key(self) -> str | None:
        return None

    @property
    def scanner_mongo_document_class(self):
        raise NotImplementedError

    def _do_your_scanning_job(self):
        raise NotImplementedError

    @property
    def kwargs_for_building_scanning_request(self) -> dict:
        return {}

    @property
    def additional_filter_fields(self) -> dict:
        return {}

    @property
    def _filter_dict(self) -> dict:
        x = {'ooi': self.next_ooi_obj.ooi,
             'scanner': self.scanning_request.scanner_id}
        x.update(self.additional_filter_fields)
        return x

    @property
    def _redis_lock_name(self):
        return str(hashlib.md5(f'lock._{self._filter_dict}'.encode()).hexdigest())

    @property
    def get_last_valid_result_filter(self) -> dict:
        x = self._filter_dict
        x.update({'_id': {'$gte': ObjectId.from_datetime(
            (datetime.datetime.utcnow() - datetime.timedelta(seconds=self.scanning_request.time_valid_response)))}})
        return x

    @property
    def _redis_cache_key(self):
        return str(hashlib.md5(f'{self._filter_dict}'.encode()).hexdigest())

    @property
    def meta_data_as_son(self) -> SON:
        if self.next_ooi_obj.meta_data_as_son:
            return self.next_ooi_obj.meta_data_as_son
        else:
            return self.scanning_request.meta_data_as_son

    def set_up(self, scanner_id: ObjectId):
        self._scanner_document = self.scanner_mongo_document_class.objects.get(id=scanner_id)

    def _set_up_quota(self):
        if self.quota_cache_key and not self.quota:
            self.quota = QuotaMechanic(cache_key=self.quota_cache_key)

    def scan(self, scanning_request, next_ooi: OOI):
        self.scanning_request = scanning_request
        self._set_up_quota()
        if self.scanning_request.time_valid_response and self.scanning_request.time_valid_response > 0:
            self._time_valid_response = self.scanning_request.time_valid_response
        else:
            self._time_valid_response = self._scanner_document.time_valid_response
        self.next_ooi_obj = next_ooi
        self.scanning_result = None
        try:
            if self.scanning_request.force:
                self._process_scanning_request()
            else:
                self._get_redis_cache()
                if self.scanning_result:
                    if self._check_if_redis_cache_not_to_old():
                        self._update_tags()
                    else:
                        self._process_scanning_request()
                else:
                    self._get_last_database_result()
                    if self._check_if_mongodb_cache_not_to_old():
                        self._update_tags()
                        self._save_scanning_result_to_redis()
                    else:
                        self._process_scanning_request()

        except RetryException:
            raise
        except Exception:
            self._logger.error(traceback.format_exception(*sys.exc_info()))
            raise
        finally:
            if self._redis_lock:
                try:
                    self._redis_lock.release()
                except Exception:
                    pass

    def _build_scanning_result(self):
        self.scanning_result = self.result_class.build_new_request(meta_data=self.meta_data_as_son, ooi=str(self.next_ooi_obj.ooi),
                                                                   scanner=self._scanner_document,
                                                                   ownership=self.scanning_request.get_ownership_obj, **self.kwargs_for_building_scanning_request)

    def _process_scanning_request(self):
        try:
            self._build_scanning_result()
            self._check_quota()
            self._redis_lock = redis_lock.Lock(self._redis_cache.redis_connection, name=self._redis_lock_name,
                                               expire=self._scanner_document.max_wait_time_for_cache)
            if self._redis_lock.acquire():
                self._do_your_scanning_job()
            elif not self._wait_for_valid_result():
                self._do_your_scanning_job()
        except (QMinute, QDay) as e:
            self._logger.debug(f'Quota block: {e}')
            self.scanning_result.quota_exception = f'{e}'
        except (MinuteBlockException, DayBlockException) as e:
            ex_str = f'{e}'
            match ex_str:
                case 'DayBlock':
                    self.quota.set_day_block()
                case 'MinuteBlock':
                    self.quota.set_minute_block()
            self._logger.debug(f'Quota block: {ex_str}')
            self.scanning_result.quota_exception = f'{ex_str}'
        finally:
            self._save_new_scanning_result()

    def _check_if_redis_cache_not_to_old(self, ):
        if (datetime.datetime.utcnow() - self.scanning_result.katti_create).seconds < self._time_valid_response:
            return True
        else:
            return False

    def _get_redis_cache(self):
        self.scanning_result = self._redis_cache.get_mongoengine_cache(mongoengine_cls=self.result_class,
                                                                       cache_key=self._redis_cache_key)

    def _get_last_database_result(self):
        try:
            self.scanning_result = list(self.result_class.objects(__raw__=self.get_last_valid_result_filter))[-1]
        except Exception:
            self.scanning_result = None

    def _check_if_mongodb_cache_not_to_old(self):
        if not self.scanning_result or not (datetime.datetime.utcnow() - self.scanning_result.katti_create).seconds < self._time_valid_response:
            return False
        return True

    def _save_scanning_result_to_redis(self):
        self._redis_cache.set_mongoengine_object(cache_key=self._redis_cache_key,
                                                 mongoengine_object=self.scanning_result,
                                                 ttl=self._scanner_document.time_valid_response)

    def _save_new_scanning_result(self):
        if self.scanning_result:
            self.scanning_result.save()
            self._save_scanning_result_to_redis()
        else:
            self._logger.error('No scanning result.')
            raise ExtremFailure('No scanning result')

    def _wait_for_valid_result(self):
        start_wait_time = datetime.datetime.now()
        while (datetime.datetime.now() - start_wait_time).seconds < self._scanner_document.max_wait_time_for_cache:
            self._get_redis_cache()
            if self.scanning_result and self._check_if_redis_cache_not_to_old():
                return True
            time.sleep(0.33)
        self._logger.debug('I have wait to long for the result.')
        return False

    def _update_tags(self):
        if self.meta_data_as_son:
            self.scanning_result.update_exiting_request_in_db(self.meta_data_as_son)

    def _check_quota(self):
        if not self.quota:
            return
        else:
            self.quota.check_day_block()
            self.quota.check_and_wait_minute_block()
