import mimetypes
from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument
from bson import ObjectId
from DataBaseStuff.MongoengineDocuments.Crawling.Link import SeleniumWireRequestURL
from mongoengine import StringField, DictField, IntField, DateTimeField, LazyReferenceField, LongField, \
    EmbeddedDocumentListField, EmbeddedDocumentField, EmbeddedDocument, BinaryField, BooleanField, DynamicField, ObjectIdField

from DataBaseStuff.MongoengineDocuments.Crawling.NeighborhoodMatrix import MatrixCell
from DataBaseStuff.MongoengineDocuments.Crawling.OutsourcedData import OutsourcedData
from Utils.HelperFunctions import convert_micro_timestamp_to_datetime
from seleniumwire.request import Request as SwRequest
from seleniumwire.request import Response as SwResponse
from seleniumwire.request import WebSocketMessage as SwWSMessage


REQUEST_LOGS = {}
REDIRECT_LOGS = {}
START_RE_LOGS = {}


class DatabaseHTTPRequest(AbstractNormalDocument):
    meta = {'collection': 'requests'}

    class Respone(EmbeddedDocument):
        date = DateTimeField()
        body = LazyReferenceField(OutsourcedData)
        headers = DictField()
        reason = StringField()
        status_code = IntField()
        body_length = LongField(default=0)

        @classmethod
        def build(cls, raw_response: SwResponse, with_save=True):
            new_response = cls(date=raw_response.date,
                               headers=raw_response.headers,
                               reason=raw_response.reason,
                               status_code=raw_response.status_code,
                               body_length=len(raw_response.body))
            new_response.body = OutsourcedData.build(data=raw_response.body, with_save=with_save)
            return new_response

    class WSMessage(EmbeddedDocument):
        content = DynamicField()
        date = DateTimeField()
        from_client = BooleanField()
        content_length = LongField(default=0)

        @classmethod
        def build(cls, raw_message: SwWSMessage, with_save=True):
            new_message = cls(date=raw_message.date,
                              from_client=raw_message.from_client)
            if raw_message.content:
                new_message.content_length = len(raw_message.content)
                new_message.content = OutsourcedData.build(data=raw_message.content, with_save=with_save)
            return new_message

    class ExtensionLogStartResponse(EmbeddedDocument):
        start = DynamicField()
        onCompleted = DateTimeField()  # TODO

        @classmethod
        def build(cls, request_id):
            global START_RE_LOGS
            if request_id in START_RE_LOGS:
                log = START_RE_LOGS.pop(request_id)
                return cls(start=log['timestamp'])

    class ExtensionLogRedirect(EmbeddedDocument):
        old_url = StringField()
        redirect_url = StringField()
        timestamp = DynamicField()

        @classmethod
        def build(cls, request_id) -> list:
            global REDIRECT_LOGS
            logs = []
            if request_id in REDIRECT_LOGS:
                raw_logs = REDIRECT_LOGS.pop(request_id)
                for log in raw_logs:
                    logs.append(cls(timestamp=log['timestamp'],
                                    old_url=log['old_url'],
                                    redirect_url=log['redirect_url']))
            return logs

    url = EmbeddedDocumentField(SeleniumWireRequestURL)

    bundle_id = ObjectIdField()

    mime_type = StringField()

    cert = DictField()
    date = DateTimeField()
    headers = DictField()
    host = StringField()
    method = StringField()

    body_length = LongField()
    body = LazyReferenceField(OutsourcedData)
    response = EmbeddedDocumentField(Respone)
    ws_messages = EmbeddedDocumentListField(WSMessage, default=[])

    # plugin_data = EmbeddedDocumentField()
    browser_request_id = StringField()
    browser_tab_id = StringField()
    browser_parent_frame_id = StringField()
    browser_frame_id = StringField()
    browser_request_type = StringField()
    browser_initiator = StringField()
    browser_timestamp = DateTimeField()

    plugin_start_response = EmbeddedDocumentField(ExtensionLogStartResponse, default=None)
    plugin_redirects = EmbeddedDocumentListField(ExtensionLogRedirect, default=[])



    # window_tab_pop_stats = EmbeddedDocumentListField(WindowTab)

    @classmethod
    def build(cls, bundle_id: ObjectId, raw_request: SwRequest, with_save=True):
        new_request = cls(date=raw_request.date,
                          host=raw_request.host,
                          headers=raw_request.headers,
                          method=raw_request.method,
                          browser_request_id=raw_request.browser_request_id,
                          browser_tab_id=raw_request.browser_tab_id,
                          browser_parent_frame_id=raw_request.parent_frame_id,
                          browser_frame_id=raw_request.frame_id,
                          browser_request_type=raw_request.type,
                          browser_timestamp=convert_micro_timestamp_to_datetime(raw_request.timestamp),
                          bundle_id=bundle_id
                          )

        url = SeleniumWireRequestURL.build(raw_request.url)
        url.set_ip(raw_request.server_ip)
        url.port = raw_request.port
        new_request.url = url
        new_request._produce_cert(raw_request.cert)
        new_request.body_length = (len(raw_request.body))
        new_request.body = OutsourcedData.build(data=raw_request.body, with_save=with_save)
        if raw_request.response:
            new_request.response = DatabaseHTTPRequest.Respone.build(raw_request.response, with_save=with_save)
        for ws_message in raw_request.ws_messages:
            new_request.ws_messages.append(DatabaseHTTPRequest.WSMessage.build(ws_message, with_save=with_save))
        new_request._guess_mime_type(raw_request.path)

        if new_request.browser_request_id:
            global REQUEST_LOGS
            if new_request.browser_request_id in REQUEST_LOGS:
                log = REQUEST_LOGS.pop(new_request.browser_request_id)
                if log.get('initiator') and not log['initiator'] == 'null':
                    new_request.browser_initiator = log['initiator']
                elif not new_request.browser_initiator:
                    new_request.browser_initiator = None
            new_request.plugin_redirects = DatabaseHTTPRequest.ExtensionLogRedirect.build(new_request.browser_request_id)

        if new_request.browser_initiator and not new_request.browser_initiator == 'undefined':
            MatrixCell.build(with_save=with_save, row=new_request.url.domain,
                                 colum=new_request.browser_initiator.split('://')[1],
                                 bundle_id=bundle_id)
        if with_save:
            new_request.save()
        return new_request

    def _produce_cert(self, raw_request_cert):
        self.cert = DatabaseHTTPRequest.produce_cert(raw_request_cert)


    @staticmethod
    def produce_cert(value, key=""):
        if isinstance(value, dict):
            return {key: DatabaseHTTPRequest.produce_cert(value, key) for key, value in value.items()}
        elif isinstance(value, list):
            return [DatabaseHTTPRequest.produce_cert(item) for item in value]
        elif isinstance(value, tuple):
            return DatabaseHTTPRequest._decode_byte_str(value[0]), DatabaseHTTPRequest._decode_byte_str(value[1])
        match key:
            case 'serial':
                return {'as_hex': hex(value), 'as_str': str(value)}
            case "notbefore" | "notafter" | "expired" | "last_update":
                return value
            case _:
                return DatabaseHTTPRequest._decode_byte_str(value)

    @staticmethod
    def _decode_byte_str(str_bytes):
        try:
            return str_bytes.decode()
        except Exception:
            return str_bytes

    def _guess_mime_type(self, path):
        try:
            x = mimetypes.guess_type(path)
            if not x[0]:
                self.mime_type = 'unknown'
            else:
                self.mime_type = x[0]
        except Exception:
            self.mime_type = 'unknown'
