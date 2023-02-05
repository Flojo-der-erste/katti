import datetime
import logging
from typing import Type
import celery
from pydantic import Field
from pydantic.dataclasses import dataclass
from Scanner.Farsight.Farsight import FarsightQuerries, Farsight
from Scanner.SSLScanner.SSLScanner import DomainsIPsForSSLScanning, SSLScanner
from Scanner.BaseScanner import RetryException, BaseScanner, BaseScanningRequestForScannerObject, Config
from Scanner.Shodan.Shodan import ShodanScanningRequest, ShodanScanner
from Scanner.Traceroute.Traceroute import DomainsIpsTraceroute, Traceroute
from Scanner.VirusTotal.VirusTotal import VirusTotal, IOCsForVTRequest
from Scanner.GSB.GoogleSafeBrowsing import GoogleSafeBrowsing, URLsForGSBRequest
from Scanner.DNS.DNSResolver import DNSResolver, DomainsForDNSResolverRequest
from bson import ObjectId
from CeleryApps.KattiApp import katti_app
from DataBaseStuff.ConnectDisconnect import connect_to_database
from DataBaseStuff.MongoengineDocuments.StatisticDocuments.ScannerTaskStatistics import ScannerTaskStats


@dataclass(config=Config)
class ScanningTaskResponse:
    scanner_id: ObjectId
    endpoint: str
    results: list = Field(default_factory=list)
    left_overs: list = Field(default_factory=list)


@dataclass(config=Config)
class ExecutionInformation:
    task: celery.Task
    scanner: BaseScanner
    statistics: ScannerTaskStats
    logger: logging.Logger
    results: list
    request_obj: BaseScanningRequestForScannerObject
    retry_counter: int


def get_task_id(task):
    task_id = task.request.id
    if not task_id:
        task_id = 'test'
    return task_id


def while_loop(execution_information: ExecutionInformation):
    response = ScanningTaskResponse(scanner_id=execution_information.scanner._scanner_document.id, endpoint=execution_information.task.name)
    next_ooi_obj = execution_information.request_obj.next_ooi_obj
    try:
        while next_ooi_obj:
            single_stats = ScannerTaskStats.SingleScannerStats(ooi=str(next_ooi_obj.ooi))
            start = datetime.datetime.utcnow()
            execution_information.scanner.scan(execution_information.request_obj, next_ooi=next_ooi_obj)
            if execution_information.scanner.scanning_result:
                execution_information.results.append(execution_information.scanner.scanning_result)
            single_stats.duration_micro_secs = (datetime.datetime.utcnow() - start).microseconds
            execution_information.statistics.single_scan_ooi_stats.append(single_stats)
            next_ooi_obj = execution_information.request_obj.next_ooi_obj
    except RetryException:
        handle_retry_exception(execution_information)
    except Exception:
        handle_normale_exception(execution_information)
    else:
        execution_information.logger.debug('Perfect, finished')
        response.results = execution_information.results
        response.left_overs = execution_information.request_obj.oois
        execution_information.statistics.oois_left_over = len(execution_information.request_obj.oois)
        execution_information.statistics.stop_and_save()
        return response


def handle_retry_exception(execution_information: ExecutionInformation):
    execution_information.request_obj.oois.append(execution_information.next_ooi_obj)
    execution_information.statistics.oois_left_over = len(execution_information.request_obj.oois)
    execution_information.statistics.stop_and_save()
    execution_information.task.retry(args=(execution_information.request_obj, execution_information.results), kwargs={'retry_counter': execution_information.retry_counter + 1})


def handle_normale_exception(exevution_information: ExecutionInformation):
    exevution_information.statistics.error = True
    exevution_information.statistics.oois_left_over = len(exevution_information.request_obj.oois)
    exevution_information.statistics.stop_and_save()
    raise


def set_up_and_execute_task(task: celery.Task, scanning_request, scanner_cls: Type[BaseScanner], retry_counter,
                            results=None, **kwargs):
    if results is None:
        results = []
    connect_to_database()
    logger = logging.getLogger(
        f'{task.name}_{scanning_request.scanner_id}<:>{scanning_request.get_ownership_obj.owner}')
    statistics = ScannerTaskStats.get_task_with_times(task_id=get_task_id(task),
                                                      scanner_task=task.name,
                                                      scanner_id=scanning_request.scanner_id,
                                                      retry_counter=retry_counter,
                                                      initiator=scanning_request.get_ownership_obj.owner,
                                                      **kwargs.get('statistics', {}))
    scanner = scanner_cls(logger=logger)
    scanner.set_up(scanning_request.scanner_id)
    return while_loop(ExecutionInformation(task=task,retry_counter=kwargs.get('retry_counter', 0), scanner=scanner,statistics=statistics, logger=logger, results=results, request_obj=scanning_request))


@katti_app.task(bind=True, max_retries=3, retry_backoff=True, default_retry_delay=0.3)
def dns_scanning_task(self, scanning_request: DomainsForDNSResolverRequest, results: list | None = None, *args,
                      **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=DNSResolver, retry_counter=kwargs.get('retry_counter', 0), results=results)


@katti_app.task(bind=True)
def gsb_scanning_task(self, scanning_request: URLsForGSBRequest, results: list | None = None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=GoogleSafeBrowsing, results=results, retry_counter=kwargs.get('retry_counter', 0))


@katti_app.task(bind=True)
def vt_scanning_task(self, scanning_request: IOCsForVTRequest, results: list | None = None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=VirusTotal, results=results, retry_counter=kwargs.get('retry_counter', 0))


@katti_app.task(bind=True)
def shodan_api_call_task(self, scanning_request: ShodanScanningRequest, results: list | None = None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=ShodanScanner, results=results, retry_counter=kwargs.get('retry_counter', 0))


@katti_app.task(bind=True)
def ssl_scanning_task(self, scanning_request: DomainsIPsForSSLScanning, results: list | None = None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=SSLScanner, results=results, retry_counter=kwargs.get('retry_counter', 0))


#@katti_app.task(bind=True)
#def misp_scanning_task(self, scanning_request: MISPScanningRequestObject, results=None, *args, **kwargs):
#    raise Exception


@katti_app.task(bind=True)
def farsight_scanning_task(self, scanning_request: FarsightQuerries, results: list | None=None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=Farsight, results=results, retry_counter=kwargs.get('retry_counter', 0))


@katti_app.task(bind=True)
def traceroute_scanning_task(self, scanning_request: DomainsIpsTraceroute, results: list | None=None, *args, **kwargs):
    return set_up_and_execute_task(task=self, scanning_request=scanning_request, scanner_cls=Traceroute, results=results, retry_counter=kwargs.get('retry_counter', 0))
