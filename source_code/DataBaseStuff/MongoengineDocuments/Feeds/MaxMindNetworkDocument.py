import ipaddress

from mongoengine import Document, StringField, IntField, DateTimeField


class Network(Document):
    meta = {'collection': 'maxmind_network',
            'db_alias': 'Katti',
            'indexes': [{'fields': ['cidr']}]}

    ip_type = StringField(choices=['ipv4', 'ipv6'], default='ipv4')
    cidr = StringField()
    range_start = IntField()
    range_stop = IntField()
    last_seen = DateTimeField()

    @staticmethod
    def get_network_from_cidr(cidr, type='ipv4'):
        network = [0]
        match type:
            case 'ipv4':
                network = list(ipaddress.IPv4Network(cidr))
            case 'ipv6':
                pass
                # range is to big -> more RAM
        try:
            network_object = Network.objects.get(cidr=cidr) #find_one -> schneller als update-One mith upsert
        except Exception:
            network_object = Network.objects(cidr=cidr).modify(__raw__={'$set': {'range_start': int(network[0]),
                                                                                 'range_stop': int(network[-1]),
                                                                                 'ip_type': type}},
                                                               upsert=True,
                                                               new=True)
        return network_object
