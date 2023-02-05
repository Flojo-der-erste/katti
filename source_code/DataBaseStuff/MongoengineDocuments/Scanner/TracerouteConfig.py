from bson import SON
from mongoengine import  ListField, IntField
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests


class TracerouteConfig(BaseScannerDocument):
    pass


class TracerouteAnswer(BaseScanningRequests):
    meta = {'collection': 'traceroute_requests'}
    hops = ListField()
    hops_counter = IntField(min_value=0, default=0)

    def update_exiting_request_in_db(self, new_meta_data_as_SON: SON):
        TracerouteAnswer.objects(id=self.id).modify(__raw__={'$addToSet': {'katti_meta_data': new_meta_data_as_SON}})


