from bson import SON
from mongoengine.fields import dateutil, DateTimeField
from mongoengine import StringField, LazyReferenceField, ListField
from pymongo import UpdateOne
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests, BaseScanningResults


class ShodanScannerDB(BaseScannerDocument):
    api_key = StringField(required=True)


class ShodanBaseResult(BaseScanningResults):
    meta = {'collection': 'shodan_crawler_results', 'allow_inheritance': True,
            'indexes': [('hash_str')]}
    hash_str = StringField(required=True)


class ShodanCrawlerResult(ShodanBaseResult):
    pass


class ShodanMeta(ShodanBaseResult):
    pass


class ShodanScanRequest(BaseScanningRequests):
    meta = {'collection': 'shodan_requests'}
    crawler_results = ListField(LazyReferenceField(ShodanCrawlerResult))
    shodan_meta = LazyReferenceField(ShodanMeta)
    shodan_last_update = DateTimeField()
    api_error = StringField(default=None)

    def update_exiting_request_in_db(self, new_meta_data_as_SON: SON):
        update = [UpdateOne({'_id': result_id}, {'$addToSet': {'meta_data': new_meta_data_as_SON}}) for result_id in self.crawler_results]
        if self.shodan_meta:
            update.append(UpdateOne({'_id': self.shodan_meta}, {'$addToSet': {'meta_data': new_meta_data_as_SON}}))
        if len(update) > 0:
            ShodanBaseResult()._get_collection().bulk_write(update)
        ShodanScanRequest.objects(id=self.id).modify(add_to_set__meta_data=new_meta_data_as_SON)


def traverse_result(value, key=""):
    if isinstance(value, dict):
        return {key: traverse_result(value, key) for key, value in value.items()}
    elif isinstance(value, list):
        return [traverse_result(item) for item in value]
    match key:
        case 'serial':
            return {'as_hex': hex(value), 'as_str': str(value)}
        case "timestamp" | "issued" | "expires" | "last_update":
            return dateutil.parser.parse(value)
        case _ if isinstance(value, int) and value > 9223372036854775807:
            return str(value)
        case _:
            return value
