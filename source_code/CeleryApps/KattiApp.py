import logging
import os
import sys

from KattiLogging.LogDocument import CeleryLog
from KattiLogging.MongoFormatter import MongoFormatter
from KattiLogging.KattiLogging import MongoHandler
from billiard import context
from celery import Celery
import celery.signals
from DataBaseStuff.ConnectDisconnect import connect_to_database
from Utils.ConfigurationClass import CeleryConfig, DatabaseConfigs


os.environ['FORKED_BY_MULTIPROCESSING'] = '1'
context._force_start_method('spawn')

celery_config = CeleryConfig.get_config()

task_routes = {'CeleryApps.ScanningTasks.*': {'queue': 'scanning'},
               'CeleryApps.PeriodicSystemTasks.*': {'queue': 'periodic_system'},
               'CeleryApps.DataFeedTasks.*': {'queue': 'data_feeds'},
               'CeleryApps.CrawlingTasks.crawling_request_celery': {'queue': 'crawling_request'},
               'CeleryApps.CrawlingTasks.crawling_task': {'queue': 'crawling_crawling'},
               'CeleryApps.CrawlingTasks.bundle_analysis': {'queue': 'crawling_analysis'}}


katti_app = Celery('katti', broker=celery_config.broker, backend=f'{DatabaseConfigs.get_config().redis_url}/0', include=[
                                                                  'CeleryApps.PeriodicSystemTasks',

                                                                  'CeleryApps.DataFeedTasks',
                                                                  'CeleryApps.CrawlingTasks'])


@celery.signals.after_setup_logger.connect
def on_celery_setup_logging(logger, *args, **kwargs):
    connect_to_database()
    if isinstance(logger.handlers[0], logging.StreamHandler):
        logger.removeHandler(logger.handlers[0])
    if len(logger.handlers) >= 1:
        return
    handler = MongoHandler()
    handler.setFormatter(MongoFormatter(log_class=CeleryLog))
    logger.addHandler(handler)
    #logger.addHandler(logging.StreamHandler(sys.stdout))


katti_app.conf.task_routes = task_routes
katti_app.conf.task_serializer = celery_config.task_serializer
katti_app.conf.result_serializer = celery_config.result_serializer
katti_app.conf.accept_content = celery_config.accept_content
