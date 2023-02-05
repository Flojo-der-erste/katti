from mongoengine import StringField, LazyReferenceField
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests, BaseScanningResults





class BaseVirusTotal(BaseScanningResults):
    meta = {'allow_inheritance': True, 'collection': 'virustotal_results'}
    hash_answer_string = StringField()


class VirusTotalUniversalURLResult(BaseVirusTotal):
    url_vt_id = StringField(required=True)


class VirusTotalUniversalIPResult(BaseVirusTotal):
    pass


class VirusTotalUniversalFileResult(BaseVirusTotal):
    pass


class VirusTotalUniversalDomainResult(BaseVirusTotal):
    pass

class VirusTotalScanningRequest(BaseScanningRequests):
    api_endpoint = StringField(required=True)
    result = LazyReferenceField(BaseVirusTotal)
    own_api_key = StringField(default=None)

    def save_scanning_result(self):
        self.save()