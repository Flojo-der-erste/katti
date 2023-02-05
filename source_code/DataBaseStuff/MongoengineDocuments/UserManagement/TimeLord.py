from mongoengine import StringField, EmailField, DateTimeField, BooleanField, EmbeddedDocument, IntField, EmbeddedDocumentListField
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument


class API(EmbeddedDocument):
    class Endpoint(EmbeddedDocument):
        endpoint_name = StringField(required=True)
        access = BooleanField(default=False, required=True)
        daily_rate = IntField(min_value=0, required=True, default=10000)

    key = StringField(min_length=28, max_length=32)
    created = DateTimeField(required=True)

    endpoints = EmbeddedDocumentListField(Endpoint, default=[])

    def has_access(self, endpoint_name):
        for endpoint in self.endpoints:
            if endpoint.endpoint_name == endpoint_name:
                if not endpoint.access:
                    return 100
                elif not endpoint.access_to_default_scanner:
                    return 200
                return 0
        return 300


class TimeLord(AbstractNormalDocument):
    meta = {'collection': 'time_lords'}

    first_name = StringField(min_length=2, max_length=50, required=True)
    last_name = StringField(min_length=2, max_length=50, required=True)
    department = StringField(min_length=2, max_length=50, required=True)
    email = EmailField(required=True, unique=True)
    pw_hash = StringField(required=True)

    created = DateTimeField()
    last_login = DateTimeField()
    las_update = DateTimeField()

    user_is_active = BooleanField(default=True)
    authenticated = BooleanField(default=False)
    anonymous = BooleanField(default=False)

  #  api = EmbeddedDocumentField(API, default=API())

    @property
    def is_active(self):
        return self.active

    def get_id(self):
        return str(self.id)

