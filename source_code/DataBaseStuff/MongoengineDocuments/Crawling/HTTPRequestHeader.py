from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from mongoengine import BooleanField, StringField, EmbeddedDocument, EmbeddedDocumentListField, ValidationError


class HTTPRequestHeader(EmbeddedDocument):
    header_field = StringField(default=None, required=True)
    header_value = StringField(default=None)
    add = BooleanField(default=True)

    def clean(self):
        if self.add and (not self.header_field or not self.header_value):
            raise ValidationError('Header field and header value is required.')


class RegexHTTPRequestHeader(EmbeddedDocument):
    regex = StringField(required=True)
    header_fields = EmbeddedDocumentListField(HTTPRequestHeader, required=True)


class UserAgentString(AbstractNormalDocument):
    meta = {'collection': 'user_agent_strings'}
    browser = StringField(required=True)
    browser_version = StringField(required=True)
    ua_string = StringField(required=True)