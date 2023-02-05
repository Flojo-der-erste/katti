import datetime
import hashlib
import magic
from mongoengine import StringField, DynamicField, DateTimeField, LongField, ListField
from DataBaseStuff.GridFsStuff import gridfs_insert_data
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument


class OutsourcedData(AbstractNormalDocument):
    meta = {'collection': 'outsourced_data',
            'indexes': [('md5_hash', 'source')]}

    mime_type = StringField(default='unknown')
    md5_hash = StringField()
    sha256_hash = StringField()
    data = DynamicField(default=None)
    last_seen = DateTimeField()

    size_in_bytes = LongField()
    create = DateTimeField()
    source = StringField(choices=['http_body', 'generated'], default='http_body')

    hashes = ListField()

    @classmethod
    def build(cls, data: bytes, with_save=True, source='http_body'):
        if isinstance(data, str):
            data = data.encode()
        md5_hash = hashlib.md5(data).hexdigest()
        sha256_hash = hashlib.sha256(data).hexdigest()
        size_in_bytes = len(data)
        mime_type = OutsourcedData._guess_data_mime_type(data)
        if data:
            if len(data) > (10 * 1048576):
                data = gridfs_insert_data(data=OutsourcedData._decode_text(data, mime_type), db_name='Katti', meta_data={'type': 'outsourced_data'})
            else:
                data = OutsourcedData._decode_text(data, mime_type)
        new_data = OutsourcedData.objects(md5_hash=md5_hash, source=source).modify(set_on_insert__data=data,
                                                                                   create=datetime.datetime.utcnow(),
                                                                                   set_on_insert__size_in_bytes=size_in_bytes,
                                                                                   set_on_insert__mime_type=mime_type,
                                                                                   set_on_insert__sha256_hash=sha256_hash,
                                                                                   set__last_seen=datetime.datetime.utcnow(),
                                                                                   upsert=True,
                                                                                   new=True)
        return new_data

    @staticmethod
    def _guess_data_mime_type(data) -> str:
        try:
            mime_type = magic.from_buffer(data, mime=True)
        except Exception:
            mime_type = 'unknown'
        return mime_type

    @staticmethod
    def _decode_text(data: bytes, mime_type: str):
        if 'text' in mime_type or 'json' in mime_type:
            try:
                data_str = data.decode('utf-8')
            except Exception:
                pass
            else:
                return data_str
        return data
