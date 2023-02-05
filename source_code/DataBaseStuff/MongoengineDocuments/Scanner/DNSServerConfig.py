import copy
import datetime
import hashlib
import json
from bson import SON
from mongoengine import StringField, ListField, EmbeddedDocument, IntField, \
    LazyReferenceField, DateTimeField, EmbeddedDocumentListField, EmbeddedDocumentField, BooleanField, DictField, \
    ValidationError
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests, BaseScanningResults
from Scanner.DNS.rdata_parser_functions import parse_soa_record, parse_a_record, parse_aaaa_record, parse_ns_record, \
    parse_dns_key_record, parse_txt_record, parse_ds_record, parse_mx_record, parse_caa_record, parse_cname_record, \
    parse_ptr_record, parse_srv_record, parse_tlsa_record


class DNSConfig(BaseScannerDocument):

    name_server_ips = ListField(default=['8.8.8.8'], required=True)

    a_record_evaluation = DictField(default=None)
    aaaa_record_evaluation = DictField(default=None)

    quad9_authority_check = BooleanField(default=False)

    allowed_record_types = ListField(required=True)
    possible_flags = ListField()
    dnsbl = BooleanField(default=False)
    name_server_dnsbl = StringField(default=None)

    def clean(self):
        if self.dnsbl and not self.name_server_dnsbl:
            raise ValidationError('Field name_server_dnsbl is is missing')
        if self.dnsbl:
            self.name_server_ips = ['0.0.0.0']


class DNSResult(BaseScanningResults):
    meta = {'collection': 'dns_results',
            'indexes': [{'fields': ['hash_answer_string']}]}

    class Question(EmbeddedDocument):
        name = StringField()
        type = StringField(default='ANY')

    class GeneralDNSType(EmbeddedDocument):
        name = StringField()
        ttl = IntField()
        type = StringField()
        data = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(name=raw_json_record['name'],
                       ttl=raw_json_record['ttl'],
                       data=raw_json_record['data'],
                       type=raw_json_record['type'])

    class SOARecord(EmbeddedDocument):
        ttl = IntField()
        mname = StringField()
        rname = StringField()
        serial = IntField()
        update = IntField()
        retry = IntField()
        expire = IntField()

        @classmethod
        def build(cls, raw_json_record, with_type=False):
            return cls(ttl=raw_json_record['ttl'], **parse_soa_record(raw_json_record['data']))

    class ARecord(EmbeddedDocument):
        ttl = IntField()
        ipaddress = StringField()
        ip_int = IntField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_a_record(raw_json_record['data']))

    class AAAARecord(EmbeddedDocument):
        ttl = IntField()
        ipaddress = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_aaaa_record(raw_json_record['data']))

    class NSRecord(EmbeddedDocument):
        ttl = IntField()
        target = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_ns_record(raw_json_record['data']))

    class DNSKeyRecord(EmbeddedDocument):
        algorithms_flag = IntField()
        protocol = IntField()
        algorithms_id = IntField()
        key = StringField()
        ttl = IntField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_dns_key_record(raw_json_record['data']))

    class TXTRecord(EmbeddedDocument):
        text = StringField()
        ttl = IntField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_txt_record(raw_json_record['data']))

    class DSRecord(EmbeddedDocument):
        ttl = IntField()
        key_tag = IntField()
        algorithm = IntField()
        digest_type = IntField()
        digest = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_ds_record(raw_json_record['data']))

    class MXRecord(EmbeddedDocument):
        ttl = IntField()
        priority = IntField()
        mail_host = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_mx_record(raw_json_record['data']))


    class CAARecord(EmbeddedDocument):
        ttl = IntField()
        flag  = IntField()
        tag = StringField()
        value = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_caa_record(raw_json_record['data']))


    class CNAMERecord(EmbeddedDocument):
        ttl = IntField()
        cname = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_cname_record(raw_json_record['data']))

    class PTRRecord(EmbeddedDocument):
        ttl = IntField()
        target = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_ptr_record(raw_json_record['data']))

    class SRVRecord(EmbeddedDocument):
        ttl = IntField()
        service = StringField()
        priority = IntField()
        weight = IntField()
        port = IntField()
        target = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_srv_record(raw_json_record['data']))

    class TLSARecord(EmbeddedDocument):
        ttl = IntField()
        host = StringField()
        usage = IntField()
        selector = BooleanField()
        matching_type = IntField()
        hash = StringField()

        @classmethod
        def build(cls, raw_json_record):
            return cls(ttl=raw_json_record['ttl'], **parse_tlsa_record(raw_json_record['data']))



    hash_answer_string = StringField()

    domain = StringField()
    dns_type = StringField(default='ANY')
    raw_answer_dig_str = StringField()
    additional_num = IntField()
    answer_num = IntField()
    authority_num = IntField()
    flags = ListField()
    opcode = StringField()
    opt_pseudosection = ListField()
    server = StringField()
    status = StringField()

    axfr = ListField()

    SOA_record = EmbeddedDocumentField(SOARecord, default=None)
    A_record = EmbeddedDocumentField(ARecord, default=None)
    AAAA_record = EmbeddedDocumentField(AAAARecord, default=None)
    NS_records = EmbeddedDocumentListField(NSRecord, default=None)
    MX_records = EmbeddedDocumentListField(MXRecord, default=None)
    TXT_records = EmbeddedDocumentListField(TXTRecord, default=None)
    DNS_Key_records = EmbeddedDocumentListField(DNSKeyRecord, default=None)
    DS_records = EmbeddedDocumentListField(DSRecord, default=None)
    CAA_records = EmbeddedDocumentListField(CAARecord, default=None)
    CNAME_records = EmbeddedDocumentListField(CNAMERecord, default=None)
    PTR_records = EmbeddedDocumentListField(PTRRecord, default=None)
    SRV_records = EmbeddedDocumentListField(SRVRecord, default=None)
    TLSA_records = EmbeddedDocumentListField(TLSARecord, default=None)

    records = EmbeddedDocumentListField(GeneralDNSType, default=None)
    scanner = LazyReferenceField(BaseScannerDocument)

    blocked = BooleanField(default=False)
    blocking_reason = StringField(default=None)


#    a_geo_data = EmbeddedDocumentListField()


class DNSRequest(BaseScanningRequests):
    meta = {'collection': 'dns_request'}

    class DNSQuery(EmbeddedDocument):
        dig_dns_id = IntField()
        query_num = IntField(default=0, min_value=0)
        query_time_ms = IntField(min_value=0)
        dig_when_time = DateTimeField()

        nameserver_ip = StringField()
        status = StringField()

        dns_response = LazyReferenceField(DNSResult)

        def build_response(self, answer_json, scanner, ownership: Ownership, a_record_evalution: dict = None,
                           aaaa_record_evalution: dict = None, quad9_auth_check=False):
            if 'when_epoch' in answer_json:
                del answer_json['when_epoch']
            if 'when_epoch_utc' in answer_json:
                del answer_json['when_epoch_utc']
            try:
                self.dig_dns_id = answer_json.pop('id')
            except Exception:
                self.dig_dns_id = 0
            try:
                self.query_time_ms = answer_json.pop('query_time')
            except Exception:
                self.query_time_ms = 0
            try:
                self.query_num = answer_json.pop('query_num')
            except Exception:
                self.query_num = 0
            try:
                self.dig_when_time = datetime.datetime.strptime(answer_json.pop('when'), '%a %b %d %H:%M:%S %Z %Y')
            except Exception:
                self.dig_when_time = None
            try:
                sorted_answer = sorted(answer_json['answer'], key=lambda d: d['data'])
            except Exception:
                pass
            else:
                answer_json['answer'] = sorted_answer
            answer_copy = copy.deepcopy(answer_json)
            question = answer_json.pop('question')
            if 'answer' in answer_json:
                answers = answer_json.pop('answer')
                dns_response = DNSResult(**answer_json)
                while len(answers) > 0:
                    next_answer = answers.pop()
                    next_answer['name'] = next_answer['name'].rstrip('.')
                    match next_answer['type']:
                        case 'DS':
                            if not dns_response.DS_records:
                                dns_response.DS_records = []
                                dns_response.DS_records.append(DNSResult.DSRecord.build(next_answer))
                        case 'DNSKEY':
                            if not dns_response.DNS_Key_records:
                                dns_response.DNS_Key_records = []
                            dns_response.DNS_Key_records.append(DNSResult.DNSKeyRecord.build(next_answer))
                        case 'SOA':
                            dns_response.SOA_record = DNSResult.SOARecord.build(next_answer)
                        case 'A':
                            dns_response.A_record = DNSResult.ARecord.build(next_answer)
                        case 'AAAA':
                            dns_response.AAAA_record = DNSResult.AAAARecord.build(next_answer)
                        case 'NS':
                            if not dns_response.NS_records:
                                dns_response.NS_records = []
                            dns_response.NS_records.append(DNSResult.NSRecord.build(next_answer))
                        case 'MX':
                            if not dns_response.MX_records:
                                dns_response.MX_records = []
                            dns_response.MX_records.append(DNSResult.MXRecord.build(next_answer))
                        case 'TXT':
                            if not dns_response.TXT_records:
                                dns_response.TXT_records = []
                            dns_response.TXT_records.append(DNSResult.TXTRecord.build(next_answer))
                        case 'CAA':
                            if not dns_response.CAA_records:
                                dns_response.CAA_records = []
                            dns_response.CAA_records.append(DNSResult.CAARecord.build(next_answer))
                        case 'CNAME':
                            if not dns_response.CNAME_records:
                                dns_response.CNAME_records = []
                            dns_response.CNAME_records.append(DNSResult.CNAMERecord.build(next_answer))
                        case 'PTR':
                            if not dns_response.PTR_records:
                                dns_response.PTR_records = []
                            dns_response.PTR_records.append(DNSResult.PTRRecord.build(next_answer))
                        case 'SRV':
                            if not dns_response.SRV_records:
                                dns_response.SRV_records = []
                            dns_response.SRV_records.append(DNSResult.SRVRecord.build(next_answer))
                        case 'TLSA':
                            if not dns_response.TLSA_records:
                                dns_response.TLSA_records = []
                            dns_response.TLSA_records.append(DNSResult.TLSARecord.build(next_answer))
                        case _:
                            if not dns_response.records:
                                dns_response.records = []
                            dns_response.records.append(DNSResult.GeneralDNSType.build(next_answer))
            else:
                dns_response = DNSResult(**answer_json)

            dns_response.dns_type = question['type']
            dns_response.katti_create = datetime.datetime.utcnow()
            dns_response.ownership = ownership
            self.status = dns_response.status
            answer_copy.update({'scanner': f'{scanner._scanner_document.id}', 'a_evalution': None, 'aaaa_evalution': None})
            if self.status == 'NOERROR':
                if a_record_evalution and dns_response.A_record:
                    dns_response.blocked = True
                    dns_response.blocking_reason = a_record_evalution.get(dns_response.A_record.ipaddress, '')
                    answer_copy.update({'a_evalution': dns_response.blocking_reason})
                if aaaa_record_evalution and dns_response.AAAA_record:
                    dns_response.blocked = True
                    dns_response.blocking_reason = aaaa_record_evalution.get(dns_response.AAAA_record.ipaddress, '')
                    answer_copy.update({'aaaa_evalution': dns_response.blocking_reason})
            if self.status == 'NXDOMAIN' and quad9_auth_check:
                if answer_json.get('authority_num', -1) == 0:
                    dns_response.blocked = True
                    dns_response.blocking_reason = 'Quad9'
                    answer_copy.update({'quad9': 'blocked'})

            json_string = json.dumps(answer_copy)
            hash_answer_string = hashlib.md5(json_string.encode()).hexdigest()
            self.dns_response = DNSResult.get_result_from_db(filter={'hash_answer_string': hash_answer_string},
                                                             ooi=question['name'].rstrip('.'),
                                                             scanner_obj=scanner,
                                                             set_on_insert_dict=dns_response.to_mongo())
            return self

    queries = EmbeddedDocumentListField(DNSQuery, default=[])
    query_counter = IntField(default=0, min_value=0)

    dig_dns_type = StringField()
    dig_flags = ListField(default=None)

    def update_exiting_request_in_db(self, new_meta_data_as_SON: SON):
        DNSRequest.objects(id=self.id).modify(__raw__={'$addToSet': {'katti_meta_data': new_meta_data_as_SON}})
        for query in self.queries:
            if query.dns_response:
                DNSResult.objects(id=query.dns_response.id).modify(__raw__={'$addToSet': {'katti_meta_data': new_meta_data_as_SON}})


