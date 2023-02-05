import datetime
import logging
from bson import ObjectId
from mongoengine import get_db
from DataBaseStuff.ConnectDisconnect import connect_to_database
from CeleryApps.KattiApp import katti_app
from DataBaseStuff.MongoengineDocuments.PeriodicTasks.DatabaseStatDocument import DatabaseStatDocument, \
    CollectionStatDocument
from PerodicSystemTasks.DatabaseStatsCalculation.DatabaseStatsCalculation import DatabaseStatsCalculation
from DataBaseStuff.MongoengineDocuments.StatisticDocuments.DatabaseStatsTaskStatistics import DatabaseStatsTaskStats


@katti_app.task(bind=True)
def db_stats(self, document_id):
    connect_to_database()
    logger = logging.getLogger('DB-Stats-Calculater')
    task_stats = DatabaseStatsTaskStats.get_task_with_times(task_id=self.request.id, initiator=None)
    try:
        db_stats_document: DatabaseStatsCalculation = DatabaseStatsCalculation.objects.get(id=ObjectId(document_id))
        logger.debug('Start stat production.')
        today = datetime.datetime.today()
        db = get_db('Katti')
        stst = db.command('dbStats', scale=db_stats_document.scale)
        new_db = DatabaseStatDocument(name='Katti', day=today)
        new_db.collections = stst['collections']
        new_db.avgObjSize = stst['avgObjSize']
        new_db.dataSize = stst['dataSize']
        new_db.storageSize = stst['storageSize']
        new_db.indexes = stst['indexes']
        new_db.indexSize = stst['indexSize']
        new_db.save()
        for collection in db.list_collection_names():
            if collection in db_stats_document.skip_collections:
                continue
            collection_stats = db.command("collstats", collection)
            new_col = CollectionStatDocument(database_name='Katti', name=collection, day=today)
            new_col.size = collection_stats['size']
            new_col.count = collection_stats.get('count', -1)
            new_col.avgObjSize = collection_stats.get('avgObjSize', 0)
            new_col.storageSize = collection_stats['storageSize']
            new_col.nindexes = collection_stats['nindexes']
            new_col.totalIndexSize = collection_stats['totalIndexSize']
            new_col.save()
        logger.debug('Done.')
    except Exception:
        task_stats.error = True
        raise
    finally:
        task_stats.stop_and_save()
