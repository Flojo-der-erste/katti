import datetime
import logging
import sys
import traceback
from pydoc import locate
from bson import ObjectId
from DataBaseStuff.MongoengineDocuments.StatisticDocuments import FeedTaskStatistics
from DataBaseStuff.ConnectDisconnect import connect_to_database
from CeleryApps.KattiApp import katti_app


@katti_app.task(bind=True)
def execute_feed(self, feed_id, model_name):
    connect_to_database()
    logger = logging.getLogger(f'{model_name}<:>{feed_id}')
    logger.debug(f'Feed model {model_name}')
    stats = FeedTaskStatistics.get_task_with_times(initiator=ObjectId(feed_id), task_id=self.request.id)
    try:
        model = locate(f'DataFeeds.{model_name}.{model_name}.{model_name}')
        feed = model.objects.get(id=ObjectId(feed_id))
        feed.fetch_feed_data(logger)
    except Exception:
        stats.error = True
        logger.error(traceback.format_exception(*sys.exc_info()))
        raise
    else:
        stats.entries_counter = feed.entry_counter
        feed.last_complete_run = datetime.datetime.utcnow()
        feed.save()
        logger.debug(f'Save updated feed model')
    finally:
        stats.stop_and_save()
        #disconnect_to_database(['Katti'])
