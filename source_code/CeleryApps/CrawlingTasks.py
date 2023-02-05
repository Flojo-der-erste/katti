import logging
import time
from bson import ObjectId
from Crawling.AfterCrawlingProduction import BundleAnalyseExecutor
from Crawling.CrawlingRequestExecutor import CrawlingExecutor
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest
from CeleryApps.KattiApp import katti_app
from CeleryApps.ScanningTasks import get_task_id
from Crawling.CrawlingTask import CrawlingTask, CrawlingTaskData, CrawlingRetry
from DataBaseStuff.ConnectDisconnect import connect_to_database
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle, CeleryCrawlingOpData
from DataBaseStuff.MongoengineDocuments.StatisticDocuments.CrawlingTaskStatistics import CrawlingTaskStatistics
from RedisCacheLayer.RedisMongoCache import RedisMongoCache


@katti_app.task(bind=True)
def crawling_request_celery(self, crawling_request_id: ObjectId):
    connect_to_database()
    redis_mongo_cache = RedisMongoCache()

    crawling_request = redis_mongo_cache.get_mongoengine_cache(cache_key=f'{crawling_request_id}',
                                                               mongoengine_cls=CrawlingRequest,
                                                               mongo_filter={'id': crawling_request_id})
    crawling_config = redis_mongo_cache.get_mongoengine_cache(cache_key=f'{crawling_request.crawling_config.id}',
                                                              mongoengine_cls=CrawlingConfig,
                                                              mongo_filter={'id': crawling_request.crawling_config.id})
    logger = logging.getLogger(f'crawling_request')
    executor = CrawlingExecutor(logger=logger, mongoengine_crawling_request=crawling_request,
                                crawling_config=crawling_config,
                                celery_task=self)
    logger.debug('Start my work.')
    crawling_request.set_init('running', get_task_id(self))
    stop_signal = False
    try:
        while not executor.i_am_finished and not stop_signal:
            crawling_request.set_heartbeat()
            executor.start_execution()
            time.sleep(5)
            stop_signal = redis_mongo_cache.is_stop_signal_set(signal_id=str(crawling_request.id))
    except Exception:
        crawling_request.status = 'failure'
        raise
    else:
        if stop_signal:
            crawling_request.status = 'aborted'
        elif crawling_request.infinity_run:
            crawling_request.status = 'break'
        else:
            crawling_request.status = 'finished'
    finally:
        crawling_request.save()


@katti_app.task(bind=True, max_retries=2, retry_backoff=True, default_retry_delay=0.3)
def crawling_task(self, crawling_data: CrawlingTaskData, **kwargs):
    connect_to_database()
    logger = logging.getLogger(f'crawling_task')
    redis_cache = RedisMongoCache()
    crawling_request = redis_cache.get_mongoengine_cache(cache_key=f'{crawling_data.request_id}',
                                                         mongoengine_cls=CrawlingRequest, mongo_filter={'id': crawling_data.request_id}, ttl=0)
    statistics = CrawlingTaskStatistics.get_task_with_times(task_id=get_task_id(self),
                                                            initiator=crawling_data.request_id,
                                                            crawling_request_id=crawling_request.id)
    crawling_task_executor = CrawlingTask(crawling_data=crawling_data,
                                          logger=logger,
                                          task=self)
    backup_clones: list[Bundle] = []
    visited_id = []
    next_bundle_id = crawling_data.next_bundle_id
    crawling_operation_status = CeleryCrawlingOpData(celery_task_id=get_task_id(self), crawling_step='start')
    start_proto = True
    try:
        while next_bundle_id:
            self.update_state(state='PROGRESS', meta={'step': 'start',
                                                      'value': 1,
                                                      'bundle': str(next_bundle_id)})
            crawling_task_executor.init_bundle(next_bundle_id, crawling_operation_status)
            visited_id.append(next_bundle_id)
            if crawling_data.statefull:
                x = crawling_task_executor.next_bundle.to_mongo()
                del x['_id']
                backup_clones.append(Bundle(id=ObjectId(), clone=crawling_task_executor.next_bundle.id, **x))
            if start_proto:
                crawling_task_executor.start_protocol()
                start_proto = False
            crawling_task_executor.execute_request()
            logger.debug(f'Perfect, finished with bundle {next_bundle_id}')
            crawling_operation_status.successfull_crawling = True
            crawling_operation_status.crawling_step = 'end'
            crawling_task_executor.next_bundle.update_celery_task_status(crawling_operation_status)
            crawling_operation_status = CeleryCrawlingOpData(celery_task_id=get_task_id(self), crawling_step='start', docker_restart_counter=crawling_operation_status.docker_restart_counter)
            next_bundle_id = crawling_data.next_bundle_id
    except CrawlingRetry:
        Bundle.objects.insert(backup_clones)
        for bundle_id in visited_id:
            Bundle.objects(id=bundle_id).update_one(__raw__={'$set': {'crawling_meta_data.statefull_retry': True}})
        shutdown_executor(crawling_task_executor, statistics, crawling_operation_status, next_bundle_id)
        c = [x.id for x in backup_clones]
        c.extend(crawling_data.bundle_ids)
        crawling_data.bundle_ids = c
        self.retry(args=(crawling_data,), kwargs={'retry_counter': kwargs.get('retry_counter', 0) + 1})
    except Exception:
        shutdown_executor(crawling_task_executor, statistics, crawling_operation_status, next_bundle_id)
        raise
    if crawling_request.analyses_settings:
        for bundle_id in visited_id:
            bundle_analysis.apply_async(args=(bundle_id,))
    return [crawling_data, get_task_id(self)]


def shutdown_executor(crawling_task_executor, statistics, crawling_operation_status, next_bundle_id):
    crawling_task_executor.shutdown_protocol()
    statistics.docker_webdriver_start_timings = crawling_task_executor.docker_webdriver_start_timings
    crawling_operation_status.crawling_step = 'end'
    if next_bundle_id:
        crawling_task_executor.next_bundle.update_celery_task_status(crawling_operation_status)
    statistics.stop_and_save()


@katti_app.task(bind=True)
def bundle_analysis(self, bundle_id: ObjectId):
    connect_to_database()
    logger = logging.getLogger(f'bundle_analysis<:>{bundle_id}')
    logger.debug(f'Start analysis of {bundle_id}')
    redis_cache = RedisMongoCache()
    bundle = Bundle.objects.get(id=bundle_id)
    crawling_request = redis_cache.get_mongoengine_cache(cache_key=f'{bundle.crawling_meta_data.crawling_request_id}',
                                                         mongoengine_cls=CrawlingRequest, mongo_filter={'id': bundle.crawling_meta_data.crawling_request_id})
    if len(crawling_request.analyses_settings) == 0:
        raise Exception(f'No analyses settings for crawling request {crawling_request.id}')
    anal_executor = BundleAnalyseExecutor(bundle_id, logger)
    anal_executor.start_scanning_tasks()
    anal_executor.save_it()


#@katti_app.task(bind=True)
#def spider_mode_preparation(self, bundle_id: ObjectId, *args, **kwargs):
#    connect_to_database()
#    logger = logging.getLogger(f'spider_mode_preparation<:>{bundle_id}')
#    logger.debug(f'Start with bundle {bundle_id}')
#    redis_cache = RedisMongoCache()
#    bundle = redis_cache.get_mongoengine_cache(cache_key=CRAWLING_CACHE_KEY(f'{bundle_id}'), mongoengine_cls=Bundle)






