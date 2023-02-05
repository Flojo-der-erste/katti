import ipaddress
from mongoengine import IntField, ListField, StringField
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class TorNodesFeedEntry(BaseFeedEntry):
    meta = {'collection': 'tor_nodes', 'db_alias': 'Katti',
            'indexes': [{'fields': ['ipv4'],
                         'name': 'ipv4'},
                        {'fields': ['ipv6'],
                         'name': 'ipv6'}
                        ]}

    ipv4 = IntField()
    ipv6 = StringField()
    days = ListField()


    def _build_update_dict_for_update_one(self) -> dict:
        return {'$addToSet': {'days': {'$each': self.days}}}

    def _build_filter_dict_for_update_one(self) -> dict:
        if self.ipv4:
            return {'ipv4': self.ipv4}
        else:
            return {'ipv6': self.ipv6}

    def set_ip(self, raw_ip_string):
        try:
            self.ipv4 = int(ipaddress.IPv4Address(raw_ip_string))
        except Exception:
            self.ipv6 = raw_ip_string
        return self