from CeleryApps.ScanningTasks import *
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest
from DataBaseStuff.MongoengineDocuments.Crawling.DatabaseHTTPRequest import DatabaseHTTPRequest
from DataBaseStuff.MongoengineDocuments.Crawling.OutsourcedData import OutsourcedData
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import BundleAnalysesTracking, AnalyseTask, \
    BundleAnalyseCandidate
from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import SSLScannerExecutionInformation, \
    ShodanExecutionInformation, DNSExecutionInformation, GSBExecutionInformation, VirusTotalExecutionInformation
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData
from FastAPI.Dependencies import check_domain
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from Scanner.BaseScanner import OOI
from Scanner.SSLScanner.SSLScanner import DomainsIPsForSSLScanning
from Scanner.VirusTotal.VirusTotal import VirusTotal
from Utils.HelperFunctions import split


class BundleAnalyseExecutor:
    def __init__(self, bundle_id: ObjectId, logger):
        self._help_analyse_tracking = {}
        self._logger = logger
        self._redis_cache = RedisMongoCache()
        self._bundle: Bundle = Bundle.objects.get(id=bundle_id)
        self._crawling_request: CrawlingRequest = self._redis_cache.get_mongoengine_cache(cache_key=f'{self._bundle.crawling_meta_data.crawling_request_id}', mongoengine_cls=CrawlingRequest, mongo_filter={'id': self._bundle.crawling_meta_data.crawling_request_id})
        if len(self._crawling_request.analyses_settings) == 0:
            raise Exception(f'No analyses settings for crawling request {self._crawling_request.id}')

        for analyses_tracking in self._bundle.crawling_meta_data.analyses_tracking:
            self._help_analyse_tracking.update({analyses_tracking.task_id: analyses_tracking})

        self._ips, self._sha256, self._domains, self._urls = self._build_oois_for_scanning()
        self._bundle_analyses_candidate = BundleAnalyseCandidate(bundle_id=self._bundle.id, priority=self._crawling_request.analyses_settings.priority)

    def _get_analyse_tracking_object(self, analyse_id: str):
        x = self._help_analyse_tracking.get(str(analyse_id))
        if not x:
            x = BundleAnalysesTracking()
            self._bundle.crawling_meta_data.analyses_tracking.append(x)
            self._help_analyse_tracking.update({analyse_id: x})
        return x

    def _build_oois_for_scanning(self):
        ips, sha256 = set(), set()
        domains, urls = self._produce_links()
        for request in DatabaseHTTPRequest.objects(id__in=self._bundle.requests): #dab abfrage
            if check_domain(request.url.domain):
                domains.add(request.url.domain)
            urls.add(request.url.url_only_with_path)
            ips.add(request.url.ip_str)
            if request.response and request.response.body:
                outsourced_data = OutsourcedData.objects.only('sha256_hash').get(id=request.response.body.id)
                sha256.add(outsourced_data.sha256_hash)
        return ips, sha256, domains, urls

    def _produce_links(self):
        domains, urls = set(), set()
        for window_tab in self._bundle.window_tab_pop_attributes:
            for link in window_tab.links:
                if (link.type == 'extern' or link.type == 'unrated' and self._crawling_request.analyses_settings.external_links) or \
                        (link.type == 'internal' and self._crawling_request.analyses_settings.internal_links) or \
                        (link.type == 'social_media' and self._crawling_request.analyses_settings.social_media_links):
                    urls.add(link.url_only_with_path)
                    if check_domain(link.domain):
                        domains.add(link.domain)
        return domains, urls

    def _calculate_next_analysis_time(self, analyse_task):
        next_date = self._help_analyse_tracking.get(analyse_task.task_id).set_and_calculate_next(analysis_settings=analyse_task) if analyse_task.task_id in self._help_analyse_tracking else None
        if next_date and (not self._bundle_analyses_candidate.next_execution or next_date < self._bundle_analyses_candidate.next_execution):
            self._bundle_analyses_candidate.next_execution = next_date

    def _can_i_conduct_analysis(self, analyse_task: AnalyseTask) -> BundleAnalysesTracking | None:
        analyse_tracking = self._help_analyse_tracking.get(analyse_task.task_id)
        return analyse_tracking if (analyse_task.execution_information.max_lookups > analyse_tracking.counter or analyse_task.execution_information.max_lookups == 0) and analyse_tracking.it_is_time else None

    def save_it(self):
        if self._bundle_analyses_candidate.next_execution:
            self._bundle_analyses_candidate.save()
        Bundle.objects(id=self._bundle.id).update_one(set__crawling_meta_data__analyses_tracking=self._bundle.crawling_meta_data.analyses_tracking)

    def start_scanning_tasks(self):
        meta_data = MetaData(bundle_id=self._bundle.id, day=datetime.datetime.utcnow())
        try:
            meta_data.tag = self._bundle.crawling_meta_data.katti_meta_data.tag
        except Exception:
            pass
        for analyses_task in self._crawling_request.analyses_settings.analyse_tasks:
            next_analyses_tracking = self._can_i_conduct_analysis(analyses_task)
            if not next_analyses_tracking:
                continue
            self._calculate_next_analysis_time(analyses_task)
            next_analyses_tracking.running_tasks = []
            match analyses_task.execution_information:
                case SSLScannerExecutionInformation():
                    for domain_chunk in split(list_a=list(self._domains), chunk_size=20):
                        next_analyses_tracking.running_tasks.append(
                            ssl_scanning_task.apply_async(args=[DomainsIPsForSSLScanning(
                                oois=[OOI(raw_ooi=domain, meta_data_obj=meta_data) for domain in domain_chunk],
                                meta_data_obj=meta_data,
                                scanner_id=analyses_task.execution_information.scanner_id,
                                ownership_obj=self._bundle.crawling_meta_data.ownership,
                                time_valid_response=analyses_task.execution_information.time_valid_response)]).id)

                case ShodanExecutionInformation():
                    for ip_chunk in split(list_a=list(self._ips), chunk_size=20):
                        next_analyses_tracking.running_tasks.append(
                            shodan_api_call_task.apply_async(args=[ShodanScanningRequest(
                                oois=[OOI(raw_ooi=ip, meta_data_obj=meta_data) for ip in ip_chunk],
                                meta_data_obj=meta_data,
                                scanner_id=analyses_task.scanner_id,
                                ownership_obj=self._bundle.crawling_meta_data.ownership,
                                time_valid_response=analyses_task.time_valid_response)]).id)

                case DNSExecutionInformation():
                    for domain_chunk in split(list_a=list(self._domains), chunk_size=20):
                        next_analyses_tracking.running_tasks.append(
                            dns_scanning_task.apply_async(
                                args=[DomainsForDNSResolverRequest(scanner_id=analyses_task.execution_information.scanner_id,
                                                                   meta_data_obj=meta_data,
                                                                   time_valid_response=analyses_task.execution_information.time_valid_response,
                                                                   ownership_obj=self._bundle.crawling_meta_data.ownership,
                                                                   dig_flags=analyses_task.execution_information.dig_flags,
                                                                   dig_type=analyses_task.execution_information.dig_type,
                                                                   oois=[OOI(raw_ooi=domain,
                                                                             meta_data_obj=meta_data)
                                                                         for domain in
                                                                         domain_chunk])]).id)
                case GSBExecutionInformation():
                    for url_chunk in split(list_a=list(self._urls), chunk_size=20):
                        next_analyses_tracking.running_tasks.append(
                            gsb_scanning_task.apply_async(args=[
                                URLsForGSBRequest(time_valid_response=analyses_task.execution_information.time_valid_response,
                                                  scanner_id=analyses_task.execution_information.scanner_id,
                                                  ownership_obj=self._bundle.crawling_meta_data.ownership,
                                                  oois=[OOI(raw_ooi=url, meta_data_obj=meta_data) for url in
                                                        url_chunk])]).id)
                case VirusTotalExecutionInformation():
                    match analyses_task.execution_information.endpoint:
                        case VirusTotal.VT_URL_ENDPOINT:
                            oois = self._urls
                        case VirusTotal.VT_IP_ENDPOINT:
                            oois = self._ips
                        case VirusTotal.VT_HASH_ENDPOINT:
                            oois = self._sha256
                        case VirusTotal.VT_DOMAIN_ENDPOINT:
                            oois = self._domains
                        case _:
                            raise Exception(f'{analyses_task.execution_information.endpoint} is not supported')

                    for ooi_chunk in split(list_a=oois, chunk_size=20):
                        next_analyses_tracking.running_tasks.append(
                            vt_scanning_task.apply_async(args=[
                                IOCsForVTRequest(time_valid_response=analyses_task.execution_information.time_valid_response,
                                                 endpoint=analyses_task.execution_information.endpoint,
                                                 scanner_id=analyses_task.execution_information.scanner_id,
                                                 ownership_obj=self._bundle.crawling_meta_data.ownership,
                                                 oois=[OOI(raw_ooi=ooi, meta_data_obj=meta_data) for ooi in
                                                       ooi_chunk])]).id)
