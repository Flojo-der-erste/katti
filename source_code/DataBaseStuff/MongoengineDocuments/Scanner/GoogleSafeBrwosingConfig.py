import datetime
from bson import SON
from mongoengine import StringField, ListField, EmbeddedDocument, EmbeddedDocumentListField, IntField, \
    DateTimeField, LazyReferenceField
from DataBaseStuff.MongoengineDocuments.StatisticDocuments.BaseServiceStatistics import BaseStatistics
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument, BaseScanningRequests, BaseScanningResults


class GoogleSafeBrowserConfig(BaseScannerDocument):
    threat_types = ListField(default=["THREAT_TYPE_UNSPECIFIED", "MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                                      "POTENTIALLY_HARMFUL_APPLICATION"])
    platform_types = ListField(default=["ANY_PLATFORM"])
    gsb_server_ip = StringField(default='127.0.0.1', required=True)
    gsb_server_port = StringField(default='8080', required=True)
    api_key = StringField(required=True)


class GSBFindings(BaseScanningResults):
    meta = {'collection': 'gsb_results',
            'indexes': [('url', 'findings')]}

    class Findings(EmbeddedDocument):
        platformType = StringField()
        threatType = StringField()

    findings = EmbeddedDocumentListField(Findings, default=[])

    finding_counter = IntField(default=0, min_value=0)
    url = StringField()


class GSbRequest(BaseScanningRequests):
    meta = {'collection': 'gsb_request'}
    finding_counter = IntField(default=0, min_value=0)
    findings = LazyReferenceField(GSBFindings)

    def save_scanning_result(self):
        self.save()
    def build_response(self, answer_json, onwership: SON, meta_data: SON =None):
        new_answer = GSBFindings()
        if 'matches' in answer_json:
            for result in answer_json['matches']:
                new_answer.findings.append(
                    GSBFindings.Findings(platformType=result['platformType'], threatType=result['threatType']))
        update = {'$setOnInsert': {'create': datetime.datetime.utcnow(),
                                   'finding_counter': len(new_answer.findings),
                                   'ownership': onwership},
                  '$set': {'last': datetime.datetime.utcnow()}}
        if meta_data:
            update.update({'$addToset': {'meta_data': meta_data}})
            self.findings = GSBFindings.objects(url=self.ooi, findings=new_answer.findings).modify(__raw__=update, upsert=True,  new=True)
        return self

class GSbServerStatus(BaseStatistics):
    meta = {'collection': 'gsb_stats'}

    QueriesByDatabase = IntField()
    QueriesByCache = IntField()
    QueriesByAPI = IntField()
    QueriesFail = IntField()
    DatabaseUpdateLag = IntField()
    ttl = DateTimeField()

    error = StringField()
