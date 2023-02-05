import gridfs
from bson import ObjectId
from gridfs import GridOut
from mongoengine import get_db


def gridfs_insert_data(data: bytes, db_name: str, meta_data=None) -> ObjectId:
    if meta_data is None:
        meta_data = {}
    return gridfs.GridFS(get_db(db_name)).put(data, **meta_data)


def gridfs_get_data(db_name: str, object_id: ObjectId) -> GridOut:
    return gridfs.GridFS(get_db(db_name)).get(object_id)