import datetime
import ipaddress

from mongoengine import ListField, StringField, IntField

from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry


class MISPWarningListEntry(BaseFeedEntry):
    meta = {'collection': 'misp_warning_list',
            'db_alias': 'Katti'}
    cidr = StringField()
    ipv4_start = IntField()
    ipv4_end = IntField()

    ipv6_start = IntField()
    ipv6_end = IntField()

    ip_type = StringField(choices=['ipv4', 'ipv6'])

    domain = StringField()

    ooi = StringField()

    list_id = StringField()
    days = ListField()

    @staticmethod
    def build(ooi, type):
        new = MISPWarningListEntry()
        new.days.append(datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
        match type:
            case 'cidr':
                new.cidr = ooi
                try:
                    network = ipaddress.IPv4Network(ooi)
                except Exception:
                    try:
                        network = ipaddress.IPv6Network(ooi)
                    except Exception:
                        pass
                    else:
                        new.ip_type = 'ipv6'
                        new.ipv6_start = 0
                        new.ipv4_end = 0
                else:
                    new.ip_type = 'ipv4'
                    new.ipv4_start = network[0]
                    new.ipv4_end = network[-1]
            case 'hostname':
                new.domain = ooi
            case _:
                new.ooi = ooi
        return new

    def _build_update_dict_for_update_one(self) -> dict:
        update = {}
        mongo = self.to_mongo()
        days = mongo['days']
        del mongo['days']

        return {'$setOnInsert': mongo,
                '$addToSet': {'$each': days}}


    def _build_filter_dict_for_update_one(self) -> dict:
        if self.cidr:
            return {'cidr': self.cidr, 'list_id': self.list_id}
        elif self.domain:
            return {'domain': self.domain, 'list_id': self.list_id}
        else:
            return {'ooi': self.ooi, 'list_id': self.list_id}