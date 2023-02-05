import datetime
from DataBaseStuff.MongoengineDocuments.Crawling.URLForCrawling import URLForCrawling
from CeleryApps.CrawlingTasks import crawling_request_celery
from mongoengine import Q, MultipleObjectsReturned, DoesNotExist
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest
from KattiServices.BaseKattiSerivce import BaseKattiService


class CrawlingRequestRestarter(BaseKattiService):

    @property
    def db_document_cls(self):
        return CrawlingRequestRestarter

    def _next_control_round(self):
        for crawling_request in CrawlingRequest.objects(infinity_run=True, stop_crawling_request=False, status='break').only('id'):
            try:
                URLForCrawling.objects.only('id').get(crawling_request_id=crawling_request.id, next_lookup__lte=datetime.datetime.utcnow())
            except MultipleObjectsReturned:
                crawling_request_celery.apply_async(args=(crawling_request.id))
            except DoesNotExist:
                pass

    def _shutdown(self):
        pass

    def _init(self):
        pass

    def _prepare_service(self):
        pass