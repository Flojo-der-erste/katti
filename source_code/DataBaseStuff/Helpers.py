import datetime

import motor.motor_asyncio
from bson import ObjectId
from pymongo import ReturnDocument

from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig


def execute_bulk_ops(bulk_ops: list, collection, min_ops=100, force=False) -> list:
    if len(bulk_ops) <= 0:
        return bulk_ops
    if force or len(bulk_ops) >= min_ops:
        collection.bulk_write(bulk_ops)
        return []
    else:
        return bulk_ops


async def save_mongoengine_objc_async(mongoengine_obj, db: motor.motor_asyncio.AsyncIOMotorClient, collection_name: str):
    if not mongoengine_obj.id:
        mongoengine_obj.id = ObjectId()
    await db[collection_name].insert_one(mongoengine_obj.to_mongo())


async def async_update_mongoengine(monoengine_cls, db: motor.motor_asyncio.AsyncIOMotorClient, collection_name, filter, update, new=True):
    x = await db[collection_name].find_one_and_update(filter, update, return_document=ReturnDocument.AFTER if new else ReturnDocument.BEFORE, upsert=True)
    print(x)
    x.update({'id': x.pop('_id')})
    return monoengine_cls(**x) if x else None


async def get_mongoengine_object_async(mongoengine_cls, db: motor.motor_asyncio.AsyncIOMotorClient, collection_name: str, filter=None):
    if filter is None:
        filter = {}
    x = await db[collection_name].find_one(filter)
    x.update({'id': x.pop('_id')})
    return mongoengine_cls(**x)


async def get_async_cursor_bundle_for_crawling_request(crawling_request_id: ObjectId, db: motor.motor_asyncio.AsyncIOMotorClient,
                                                       projection=None) -> motor.motor_asyncio.AsyncIOMotorCursor:
    if projection is None:
        projection = {}
    return db['bundles'].find({'crawling_meta_data.crawling_request_id': crawling_request_id}, projection)


async def async_execute_bulk_ops(bulk_ops: list, db: motor.motor_asyncio.AsyncIOMotorClient, collection_name: str, force: bool=False, min_ops: int=0):
    if len(bulk_ops) <= 0:
        return bulk_ops
    if force or len(bulk_ops) >= min_ops:
        await db[collection_name].bulk_write(bulk_ops)
        return []
    return bulk_ops


async def async_save(db: motor.motor_asyncio.AsyncIOMotorClient, config):
    result = await db['browser_configs'].find_one_and_update({'config': config.to_mongo()}, {'$setOnInsert': {'create': datetime.datetime.utcnow()}}, upsert=True, return_document=ReturnDocument.AFTER)
    result.update({'id': result.pop('_id')})
    return BrowserConfig(**result)
