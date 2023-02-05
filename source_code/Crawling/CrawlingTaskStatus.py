import datetime
from mongoengine import StringField, EmbeddedDocument, BooleanField, IntField, DateTimeField, UUIDField, ObjectIdField

CRAWLING_STATUS = {'waiting_for_downloads'}

class CrawlerStatus(EmbeddedDocument):
    create = DateTimeField()
    status = StringField()
    execute_cmd = StringField(default=None)

    @classmethod
    def build_new_status(cls, new_status, execute_cmd='No cmd'):
        return cls(create=datetime.datetime.utcnow(),
                   status=new_status,
                   execute_cmd=execute_cmd)


class CrawlingResult(EmbeddedDocument):
    create = DateTimeField()
    error_code = IntField(default=-1)
    finished = BooleanField(default=False)

    @classmethod
    def build(cls, error_code=-1, crawling_done=False):
        return cls(create=datetime.datetime.utcnow(),
                   error_code=error_code,
                   finished=crawling_done)


