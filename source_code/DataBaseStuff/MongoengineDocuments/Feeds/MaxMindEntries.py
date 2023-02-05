from mongoengine import ListField, LazyReferenceField, IntField, StringField, BooleanField, FloatField
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry
from DataBaseStuff.MongoengineDocuments.Feeds.MaxMindASNDocument import ASN
from DataBaseStuff.MongoengineDocuments.Feeds.MaxMindNetworkDocument import Network


class CityBlockEntry(BaseFeedEntry):
    meta = {'collection': 'maxmind_city',
            'db_alias': 'Katti',
            'indexes': [{'fields': ['geoname_id', 'ip_type', 'registered_country_geoname_id', 'represented_country_geoname_id', 'is_anonymous_proxy', 'is_satellite_provider', 'network', 'postal_code', 'latitude', 'longitude', 'accuracy_radius'],
                         'name': 'main_city_block'},
                        ]}

    @property
    def entry_insert_index(self):
        return 'main_city_block'

    geoname_id = IntField()
    ip_type = StringField(choices=['ipv4', 'ipv6'])
    registered_country_geoname_id = IntField()
    represented_country_geoname_id = IntField()
    is_anonymous_proxy = BooleanField()
    is_satellite_provider = BooleanField()
    postal_code = StringField()
    latitude = FloatField()
    longitude = FloatField()
    accuracy_radius = IntField()
    days = ListField()

    network = LazyReferenceField(Network)
    _with_feed = False

    def _build_update_dict_for_update_one(self) -> dict:
        return {'$addToSet': {'days': {'$each': self.days}}}

    def _build_filter_dict_for_update_one(self) -> dict:
        update = {}
        for index in self.meta['indexes']:
            match index['name']:
                case 'main_city_block':
                    mongo = self.to_mongo()
                    for field in index['fields']:
                        if field in mongo:
                            update.update({field: mongo[field]})
        return update


class CountryBlockEntry(BaseFeedEntry):
    meta = {'collection': 'maxmind_country',
            'db_alias': 'Katti',
            'indexes': [{'fields': ['geoname_id', 'ip_type', 'registered_country_geoname_id', 'represented_country_geoname_id', 'is_anonymous_proxy', 'is_satellite_provider', 'network'],
                         'name': 'main_country_block'}]
            }



    geoname_id = IntField()
    ip_type = StringField(choices=['ipv4', 'ipv6'])
    registered_country_geoname_id = IntField()
    represented_country_geoname_id = IntField()
    is_anonymous_proxy = BooleanField()
    is_satellite_provider = BooleanField()
    network = LazyReferenceField(Network)
    days = ListField()
    _with_feed = False

    def _build_update_dict_for_update_one(self):
        return {'$addToSet': {'days': {'$each': self.days}}}

    def _build_filter_dict_for_update_one(self) -> dict:
        update = {}
        for index in self.meta['indexes']:
            match index['name']:
                case 'main_country_block':
                    mongo = self.to_mongo()
                    for field in index['fields']:
                        if field in mongo:
                            update.update({field: mongo[field]})
        return update


class LinkASNNetwork(BaseFeedEntry):
    meta = {'collection': 'maxmind_ans_network',
            'db_alias': 'Katti',
            'indexes': [{'fields': ['asn', 'network'],
                         'name': 'main_asn_network'}]
            }

    days = ListField(default=[])

    asn = LazyReferenceField(ASN)
    network = LazyReferenceField(Network)
    _with_feed = False


    def _build_update_dict_for_update_one(self):
        return {'$addToSet': {'days': {'$each': self.days}}}

    def _build_filter_dict_for_update_one(self) -> dict:
        update = {}
        for index in self.meta['indexes']:
            match index['name']:
                case 'main_asn_network':
                    mongo = self.to_mongo()
                    for field in index['fields']:
                        if field in mongo:
                            update.update({field: mongo[field]})
        return update
