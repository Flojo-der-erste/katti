import datetime
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from bson import ObjectId
from mongoengine import StringField, IntField, DateTimeField, ObjectIdField


class MatrixCell(AbstractNormalDocument):
    meta = {'collection': 'neighborhood_matrix',
            'indexes': [('row', 'colum', 'bundle_id')]}

    """row: Domain
        colum: initiator"""
    row = StringField()
    colum = StringField()
    counter = IntField(default=0)
    bundle_id = ObjectIdField()
    create = DateTimeField()

    @classmethod
    def build(cls, bundle_id: ObjectId, row: str, colum: str, with_save: bool = True):
        if colum == row:
            return
        new_cell = cls(row=row, colum=colum)
        if with_save:
            return MatrixCell.objects(row=new_cell.row, colum=new_cell.colum, bundle_id=bundle_id).modify(
                inc__counter=1,
                set_on_insert__create=datetime.datetime.utcnow(),
                upsert=True,
                new=True)
        return new_cell
