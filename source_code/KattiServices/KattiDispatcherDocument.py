import datetime
import socket

from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from bson import ObjectId
from mongoengine import StringField, DateTimeField, IntField, LazyReferenceField, ListField, BooleanField, \
    EmbeddedDocument, EmbeddedDocumentField, get_db, ObjectIdField, EmbeddedDocumentListField

from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData


class KillCandidate(EmbeddedDocument):
    service_id = ObjectIdField(required=True)
    status = StringField(choices=['not started', 'wait for dead', 'kill'])
    start_killing = DateTimeField()


class KattiDispatcherDB(AbstractNormalDocument):
    meta = {'collection': 'ServiceDispatcher',
            'db_alias': 'Katti'}
    log_level = StringField()
    station_ip = StringField(default='0.0.0.0')
    node_name = StringField(default='Test', required=True)
    last_heartbeat = DateTimeField(default=datetime.datetime.utcnow())
    max_dispatched_processes = IntField(default=30, min_value=1, required=True)

    services_counter = IntField(min_value=0, default=0)
    action = StringField(choices=['run', 'stop', 'shutdown protocol'], default='run')
    status = StringField(default='Good')

    wait_time_in_loop_s = IntField(default=1)
    shutdown_wait_time_s = IntField(default=10 * 60)

    kill_candidates = EmbeddedDocumentListField(document_type=KillCandidate, default=[])
    restart_candidates = ListField(default=[])
    with_crawling_services = BooleanField(default=True)

    @property
    def my_name(self):
        return f'{self.node_name}'

    @property
    def should_i_stop(self) -> bool:
        match self.action:
            case 'stop':
                return True
            case _:
                return False

    def set_heartbeat(self):
        time_now = datetime.datetime.utcnow()
        if (time_now - self.last_heartbeat).seconds > 60:
            self.last_heartbeat = time_now

    @staticmethod
    def register_at_system(node_name):
        return KattiDispatcherDB.objects(node_name=node_name).modify(**{'action': 'run',
                                                                        'status': 'Good',
                                                                        'station_ip': f'{socket.gethostbyname(node_name)}',
                                                                        'last_heartbeat': datetime.datetime.utcnow()},
                                                                     upsert=True,
                                                                     new=True)

    def set_stattus(self, new_status):
        self.status = new_status
        self.save()

    def get_my_running_services(self):
        pass

    @staticmethod
    def get_service_for_first_start(dispatcher_id: ObjectId, with_crawling_services):
        if with_crawling_services:
            return get_db('Katti')['KattiServices'].find_one_and_update({'dispatcher': None, 'action': 'go'}, {'$set': {'dispatcher': dispatcher_id}})
        else:
            return get_db('Katti')['KattiServices'].find_one_and_update({'_cls': {'$ne': 'KattiServiceDB.CrawlingServiceDB'}, 'dispatcher': None, 'action': 'go', },
                                                                        {'$set': {'dispatcher': dispatcher_id}})

    @staticmethod
    def get_service_for_restart(dispatcher_id: ObjectId, with_crawling_services):
        if with_crawling_services:
            return get_db('Katti')['KattiServices'].find_one_and_update({'dispatcher': dispatcher_id, 'action': 'restart'}, {'$set': {'action': 'go'}})

        else:
            return get_db('Katti')['KattiServices'].find_one_and_update({'_cls': {'$ne': 'KattiServiceDB.CrawlingServiceDB'}, 'dispatcher': dispatcher_id, 'action': 'restart'}, {'$set': {'action': 'go'}})


class CronTabKattiService(EmbeddedDocument):
    minute = StringField(default='*', required=True)
    hour = StringField(default='*', required=True)
    day_of_week = StringField(default='*', required=True)
    day_of_month = StringField(default='*', required=True)
    month_of_year = StringField(default='*', required=True)

    def to_cronjob_string(self):
        return f'{self.minute} {self.hour} {self.day_of_week} {self.day_of_month} {self.month_of_year}'


class IntervalKattiServcie(EmbeddedDocument):
    period = StringField(required=True, default='day', choices=['day', 'minute'])
    interval = IntField(min_value=1, default=1, required=True)



class KattiServiceDB(AbstractNormalDocument):
    meta = {'allow_inheritance': True,
            'collection': 'KattiServices'}

    class KillTimer(EmbeddedDocument):
        time_before_kill_seconds = IntField(min_value=1, required=True, default=60)


    rebuild_counter = IntField(default=0)
    max_rebuilds = IntField(min_value=0, default=0)

    last_heartbeat = DateTimeField(default=datetime.datetime.utcnow())
    typ = StringField(choices=['crawling', 'scanner'])
    dispatcher = LazyReferenceField(document_type=KattiDispatcherDB, default=None)
    status = StringField(choices=['running', 'break', 'finished', 'new', 'restart', 'shutdown_process'], default='new')
    action = StringField(choices=['go', 'wait', 'break', 'restart'], default='go')

    is_alive = BooleanField(default=False)
    sleep_time = IntField(min_value=0, default=1)

    up_to_date = StringField()
    process_pid = StringField(default=None)

    restart = BooleanField(default=True)


    crontab = EmbeddedDocumentField(CronTabKattiService)
    interval = EmbeddedDocumentField(IntervalKattiServcie)

    kill_timer = EmbeddedDocumentField(KillTimer, default=None)

    suicide_times = ListField(default=[])

    ownership = EmbeddedDocumentField(Ownership)
    meta_data = EmbeddedDocumentField(MetaData)

    #service_cls_name = StringField(required=True)

    _last_reload = None
    def set_heartbeat_update_and_sync(self, new_update=None, force_reload=False):
        self.set_heartbeat_update(new_update)
        if force_reload or new_update or (not self._last_reload or (datetime.datetime.utcnow() - self._last_reload).seconds > 10):
            self.reload()
            self._last_reload = datetime.datetime.utcnow()

    def set_heartbeat_update(self, new_update=None):
        time_now = datetime.datetime.utcnow()
        if (time_now - self.last_heartbeat).seconds > 60:
            self.last_heartbeat = time_now
        if new_update:
            self.up_to_date = f'[{datetime.datetime.utcnow()}] {new_update}'
        self.save()

    def set_status(self, new_status):
        print(f'dddddddddddddd {new_status}')
        self.status = new_status
        self.save()

    @staticmethod
    def set_is_alive(service_id: ObjectId, value):
        get_db('Katti')['KattiServices'].update_one({'_id': service_id}, {'$set': {'is_alive': value}})
