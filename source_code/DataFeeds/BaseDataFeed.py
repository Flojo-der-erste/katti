import datetime
import sys
import threading
import traceback
from typing import Type

from bson import ObjectId
from mongoengine import StringField, ListField, LazyReferenceField, BooleanField, get_db, DateTimeField
from pymongo import InsertOne
from pymongo.errors import BulkWriteError

from CeleryBeatMongo.models import PeriodicTask, Interval, Crontab
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord
from Utils.configurations import ALLOWED_FEED_TYPES, ACCESS_TYPES


class BaseDataFeed(PeriodicTask):
    description = StringField(default=None)
    type = StringField(default=None, choices=ALLOWED_FEED_TYPES, required=True)
    owner = LazyReferenceField(document_type=TimeLord, required=True)
    access = ListField(default=['all'], choices=ACCESS_TYPES, required=True)
    last_complete_run = DateTimeField()
    visible = BooleanField(default=True, required=True)

    ignore_bulk_write_errors = BooleanField(default=False)

    _logger = None
    _error = False
    _entry_counter = 0

    @property
    def entry_counter(self) -> int:
        return self._entry_counter

    @property
    def entry_cls(self):
        raise NotImplementedError

    def _myself(self, **kwargs):
        raise NotImplementedError

    def _produce_feed(self):
        raise NotImplementedError

    @classmethod
    def build(cls, owner, period, access, description, name, task_args, **kwargs):
        new_feed = cls(owner=owner,
                       task='CeleryApps.Tasks.execute_feed',
                       access=access,
                       description=description,
                       name=name)
        if isinstance(period, Interval):
            new_feed.interval = period
        elif isinstance(period, Crontab):
            new_feed.crontab = period
        else:
            raise Exception
        feed_id = ObjectId()
        args = [str(feed_id), str(cls.__name__)]
        args.extend(task_args)
        new_feed.id = feed_id
        new_feed.args = args
        new_feed.run_immediately = kwargs.get('run_immediately', True)
        new_feed.visible = kwargs.get('visible', True)
        new_feed._myself(**kwargs)
        #new_feed.expires = (datetime.datetime.utcnow() + datetime.timedelta(hour=12))
        return new_feed

    def fetch_feed_data(self, logger=None):
        if not logger:
            raise Exception('No logger')
        else:
            self._logger = logger
        self._logger.debug('Start fetching feed data')
        self._lock = threading.Lock()
        self.update_one = True
        self._counter = 0
        self._feed_entries = []
        self._produce_feed()
        self._save_feed_entries_update()
        self._logger.info(f'Finished fetching data. Counter: {self._counter}')

    def _save_feed_entries_update(self):
        if len(self._feed_entries) > 0:
            try:
                #self._logger.debug(f'Save entries, list length {len(self._feed_entries)}')
                self._counter += len(self._feed_entries)
                self.entry_cls()._get_collection().bulk_write(self._feed_entries, ordered=False)
            except BulkWriteError:
                if self.ignore_bulk_write_errors:
                    pass
                else:
                    self._error = True
                    self._logger.error(traceback.format_exception(*sys.exc_info()))
            except Exception:
                self._error = True
                self._logger.error(traceback.format_exception(*sys.exc_info()))
            finally:
                self._feed_entries = []

    def insert_new_entry_into_list(self, new_entry):
        with self._lock:
            if not new_entry:
                return
            new_entry.ttl = datetime.datetime.utcnow()
            if len(self._feed_entries) > 10000:
                self._save_feed_entries_update()
            try:
                new_entry.feed = self.id
                if self.update_one:
                    x = new_entry.get_update_one()
                    self._feed_entries.append(x)
                else:
                    self._feed_entries.append(InsertOne(new_entry.to_mongo()))
                self._entry_counter += 1
            except Exception:
                self._error = True
                self._logger.error(traceback.format_exception(*sys.exc_info()))


