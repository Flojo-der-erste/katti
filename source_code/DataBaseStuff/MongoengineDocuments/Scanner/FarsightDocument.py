from mongoengine import StringField, ListField, DateTimeField, IntField, DictField, BooleanField, \
    URLField, LazyReferenceField
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests, BaseScanningResults, BaseScannerDocument


class FarsightDocument(BaseScannerDocument):
    api_key = StringField(required=True)


class FarsightQuerryResult(BaseScanningResults):
    domain = StringField()
    time_first = DateTimeField()
    time_last = DateTimeField()
    count = IntField()
    bailiwick = StringField()
    type = StringField()
    record = DictField()
    freeze = BooleanField(default=False)


class FarsightRequest(BaseScanningRequests):
    farsight_querry_results = ListField(LazyReferenceField(FarsightQuerryResult))
    result_counter = IntField(default=0, min_value=0)
    url = URLField()

    def update_exiting_request_in_db(self, new_meta_data_as_SON: MetaData):
        FarsightRequest.objects(id=self.id).modify(__raw__={'$addToSet': {'katti_meta_data': new_meta_data_as_SON}})
        for querry_result in self.farsight_querry_results:
            FarsightQuerryResult.objects(id=querry_result.id).modify(__raw__={'$addToSet': {'katti_meta_data': new_meta_data_as_SON}})

