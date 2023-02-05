import datetime

from bson import SON
from mongoengine import IntField, BooleanField, StringField, EmbeddedDocument, DynamicField, \
    LazyReferenceField, EmbeddedDocumentField, EmbeddedDocumentListField, ListField, \
    DateTimeField, DictField

from DataBaseStuff.MongoengineDocuments.BaseDocuments import AbstractNormalDocument, AbstractDynamicalDocument
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests



class CipherSuite(AbstractNormalDocument):
    meta = {'collection': 'ssl_scanner_cipher_suites'}
    is_anonymous = BooleanField()
    key_size = IntField()
    name = StringField()
    openssl_name = StringField()

    @classmethod
    def get_suite(cls, raw_suite):
        return cls.objects(**raw_suite).modify(__raw__={'$setOnInsert': {}}, upsert=True, new=True)


class EphemeralKey(EmbeddedDocument):
    curve_name = StringField()
    generator = DynamicField()
    prime = DynamicField()
    public_bytes = StringField()
    size = IntField()
    type_name = StringField()
    x = StringField()
    y = StringField()
    hash_string = StringField()


class CipherSuiteEphemeralKey(EmbeddedDocument):
    cipher_suite = LazyReferenceField(CipherSuite)
    ephemeral_key = EmbeddedDocumentField(EphemeralKey, default=None)


class TLSResult(EmbeddedDocument):
    tls_version = StringField()
    error_reason = StringField(default=None)
    error_trace = DynamicField(default=None)

    accepted_cipher_suites = EmbeddedDocumentListField(CipherSuiteEphemeralKey, default=None)
    rejected_cipher_suites = EmbeddedDocumentListField(CipherSuiteEphemeralKey, default=None)
    tls_1_3_early_data = DynamicField()
    supports_compression = DynamicField()
    is_tls_version_supported = BooleanField()
    status = StringField()
    error_message = StringField()


class Certificatenfo(AbstractDynamicalDocument):
    meta = {'collection': 'ssl_scanner_cert_info'}
    katti_create = DateTimeField()
    cert_result = DictField()

    @staticmethod
    def get_certificate_info(scanner_cert_result: dict, domain):
        return Certificatenfo.objects(cert_result=scanner_cert_result).modify(set_on_insert__katti_create=datetime.datetime.utcnow(), set_on_insert__domain=domain, upsert=True, new=True)



class SSLScanResult(BaseScanningRequests):
    meta = {'collection': 'ssl_scan_results'}
    tls_ssl_scan_results = EmbeddedDocumentListField(TLSResult, default=[])
    certificate_info = LazyReferenceField(Certificatenfo)

    invalid_server_strings = DynamicField()
    sslyze_version = StringField()
    connectivity_error = BooleanField(default=False)
    port = IntField()
    scan_commands = ListField()

    def update_exiting_request_in_db(self, new_meta_data_as_SON: SON):
        SSLScanResult.objects(id=self.id).modify(add_to_set__meta_data=new_meta_data_as_SON)


class SSLScannerDB(BaseScannerDocument):
    type = StringField(default='ssl_scanner')
    allowed_scan_commands = ListField(default=['ssl_2_0_cipher_suites',
                                'ssl_3_0_cipher_suites',
                                'tls_1_0_cipher_suites',
                                'tls_1_1_cipher_suites',
                                'tls_1_2_cipher_suites',
                                'tls_1_3_cipher_suites',
                                'tls_compression',
                                'certificate_info',
                                'tls_1_3_early_data'])
