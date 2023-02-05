from mongoengine import Document, DynamicDocument, StringField


class AbstractNormalDocument(Document):
    meta = {'abstract': True,
            'db_alias': 'Katti',
            'auto_create_index': False}


class AbstractDynamicalDocument(DynamicDocument):
    meta = {'abstract': True,
            'db_alias': 'Katti',
            'auto_create_index': False}



class BaseConfig(AbstractDynamicalDocument):
    meta = {'collection': 'configurations',
            'allow_inheritance': True}

    name = StringField(required=True, unique=True)

    @staticmethod
    def collection_name() -> str:
        return 'configurations'


