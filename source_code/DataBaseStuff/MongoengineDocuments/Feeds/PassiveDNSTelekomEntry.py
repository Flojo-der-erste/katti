import datetime
import ipaddress

from mongoengine import EmbeddedDocument, IntField, StringField, DateTimeField, ListField, EmbeddedDocumentListField

from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class TelekomDNSEntry(BaseFeedEntry):
    """_id Field is Domain"""
    meta = {'collection': 'pdns_telekom', 'db_alias': 'Katti',
            'auto_create_index': False,
            'indexes': [{'fields': ['_id'],
                         'name': '_id_'}]}

    _with_validation = False
    _with_feed = False

    class IPAddress(EmbeddedDocument):
        ipv4 = IntField()
        raw_ipv4 = StringField()
        ipv6 = StringField()
        day = DateTimeField()

        @staticmethod
        def build(day, ipv4=None, ipv6=None):
            new = TelekomDNSEntry.IPAdress(day=day)
            if not ipv6 and not ipv4:
                raise Exception('Need an ip')
            if ipv4:
                try:
                    new.ipv4 = int(ipaddress.IPv4Address(ipv4))
                except Exception:
                    new.raw_ipv4 = ipv4
            if ipv6:
                new.ipv6 = ipv6
            return new

    class Cname(EmbeddedDocument):
        cname = StringField()
        day = DateTimeField()

    new_domain = DateTimeField(default=None)
    nx_domain = ListField(default=[])
    ip_adr = EmbeddedDocumentListField(IPAddress, default=[])
    cnames = EmbeddedDocumentListField(Cname, default=[])
    create = DateTimeField()

    regex_tags = ListField()


    def _build_update_dict_for_update_one(self) -> dict:
        update = {}
        add_to_set = {}
        if self.regex_tags:
            add_to_set.update({'regex_tags': {'$each': [tag for tag in self.regex_tags]}})
        if self.new_domain:
            update.update({'$min': {'new_domain': self.new_domain}})
        if self.nx_domain:
            add_to_set.update({'nx_domain': {'$each': [nxdomain for nxdomain in self.nx_domain]}})
        if len(self.ip_adr) > 0:
            add_to_set.update({'ip_adr': {'$each': [ip.to_mongo() for ip in self.ip_adr]}})
        if len(self.cnames) > 0:
            add_to_set.update({'cnames': {'$each': [cname.to_mongo() for cname in self.cnames]}})
        update.update({'$addToSet': add_to_set, '$setOnInsert': {'create': datetime.datetime.utcnow()}})
        return update

    def _build_filter_dict_for_update_one(self) -> dict:
        return {'_id': self.id}
