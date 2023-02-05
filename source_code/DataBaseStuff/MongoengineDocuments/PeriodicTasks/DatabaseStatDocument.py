from mongoengine import Document, StringField, IntField, LongField, FloatField, DateTimeField


class DBStats(Document):
    meta = {'collection': 'DatabaseStats',
            'allow_inheritance': True,
            'db_alias': 'Statistics'}

    day = DateTimeField()

class DatabaseStatDocument(DBStats):
    name = StringField()
    collections = IntField(default=None)
    objects = LongField()
    avgObjSize = FloatField()
    dataSize = FloatField()
    storageSize = FloatField()
    indexSize = FloatField()
    indexes = IntField()


class CollectionStatDocument(DBStats):
    name = StringField()
    database_name = StringField()
    size = FloatField()
    count = IntField()

    avgObjSize = FloatField()
    storageSize = FloatField()
    storage_size_mb = FloatField()
    totalIndexSize = FloatField()
    nindexes = IntField()
