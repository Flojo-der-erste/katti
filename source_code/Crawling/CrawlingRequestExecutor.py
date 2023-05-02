import datetime
import sys
import traceback
from dataclasses import dataclass, field

from mongoengine import Q, DoesNotExist

from Crawling.CrawlingTask import CrawlingTaskData
from DataBaseStuff.MongoengineDocuments.Scanner.DNSServerConfig import DNSResult
from CeleryApps.KattiApp import katti_app
from RedisCacheLayer.RedisMongoCache import RedisMongoCache, URLHeadersRedisCache
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import BundleAnalysesTracking
from Scanner.BaseScanner import OOI
from bson import ObjectId
from celery import group, Task
from celery.result import AsyncResult, GroupResult
from CeleryApps.ScanningTasks import dns_scanning_task, DomainsForDNSResolverRequest
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest, BrowserGroup
from DataBaseStuff.MongoengineDocuments.Crawling.Link import URL
from DataBaseStuff.MongoengineDocuments.Crawling.URLForCrawling import URLForCrawling
from Utils.HelperFunctions import split

BYPASS_DNS_PROOF = False

@dataclass
class GroupObserver:
    browser_group: BrowserGroup | None = None
    new_crawling_tasks_data: list = field(default_factory=list)
    group_tasks: list[GroupResult] = field(default_factory=list)
    bundle_clones: list[Bundle] = field(default_factory=list)

    @property
    def group_id(self):
        return self.browser_group.group_id if self.browser_group else None

    def finished(self) -> bool:
        if len(self.group_tasks) == 0:
                return True
        for task in self.group_tasks:
            if not task.ready():
                return False
        return True

    def group_state(self, operation_mode='waiting') -> int:
        # finished | ready for new urls -> 00(0), 11 (3),  01 (2)
        match operation_mode:
            case 'waiting':
                return 3 if self.finished() else 0
            case 'not_waiting':
                running_tasks = []
                running_single_crawling_tasks = 0
                for group_task in self.group_tasks:
                    if group_task.ready():
                        continue
                    else:
                        running_tasks.append(group_task)
                        for result in group_task.results:
                            if not result.ready():
                                running_single_crawling_tasks += 1
                self.group_tasks = running_tasks
                match running_single_crawling_tasks:
                    case 0:
                        return 3
                    case _ if running_single_crawling_tasks < 10:
                        return 2
                    case _:
                        return 0

    @property
    def crawling_task_data_count(self) -> int:
        return len(self.new_crawling_tasks_data)

    def start_crawling_tasks(self):
        try:
            from CeleryApps.CrawlingTasks import crawling_task
        except ImportError:
            import sys
            crawling_task = sys.modules[__package__ + '.crawling_task']
        task_group = group(crawling_task.s(crawlingTask_data) for crawlingTask_data in self.new_crawling_tasks_data)
        self.group_tasks.append(task_group.apply_async())
        self.new_crawling_tasks_data = []
        #self._group_task.save()

    def add_new_crawling_task(self, bundle_chunk: list[Bundle], request_id, crawling_config_id, random=True, statefull=False) -> list[Bundle]:
        clones = []
        for index, browser_config in enumerate(self.browser_group.browser_configs):
            new_crawling_task_data = CrawlingTaskData(browser_config_id=browser_config,
                                                      request_id=request_id,
                                                      group_id=self.browser_group.group_id,
                                                      random=random,
                                                      statefull=statefull,
                                                      crawling_config_id=crawling_config_id)
            for bundle in bundle_chunk:
                if index > 0:
                    x = bundle.to_mongo()
                    del x['_id']
                    bundle = Bundle(id=ObjectId(), **x)
                    clones.append(bundle)
                new_crawling_task_data.bundle_ids.append(bundle.id)
                bundle.crawling_meta_data.browser_config = browser_config
                bundle.crawling_meta_data.group_id = self.browser_group.group_id
                bundle.crawling_meta_data.crawling_request_id = request_id
            self.new_crawling_tasks_data.append(new_crawling_task_data)
        return clones


class CrawlingExecutor:
    def __init__(self, mongoengine_crawling_request, logger, crawling_config, celery_task: Task):
        self._db_obj: CrawlingRequest = mongoengine_crawling_request
        self._logger = logger
        self._crawling_config: CrawlingConfig = crawling_config
        self.i_am_finished = False
        self._dns_task = None
        self._last_fetch_from_db = None
        self._raw_analyses_tracking = []
        self._celery_task: Task = celery_task
        self._redis_cache = RedisMongoCache()

        self._group_observer: list[GroupObserver] = [GroupObserver(browser_group=browser_group) for browser_group in self._db_obj.crawling_groups]

    @property
    def is_stop_signal_set(self) -> bool:
        signal = self._redis_cache.get_value(f'stop_signal_{self._db_obj.id}')
        if not signal:
            return False
        return True

    def start_execution(self):
        if self._db_obj.analyses_settings:
            self._raw_analyses_tracking = [BundleAnalysesTracking(task_id=analyse_setting.task_id) for analyse_setting in
                                           self._db_obj.analyses_settings.analyse_tasks]
        self._groups_ready_for_new_urls = []
        self._next_bundle_chunks = []
        self._bundles_for_sync = []
        self._all_finished = False
        self._url_crawling_obj_for_sync = []
        self._dns_task = None
        self._ready_for_new_urls()
        if len(self._groups_ready_for_new_urls) <= 0:
            return
        self._get_next_urls()
        match len(self._next_bundle_chunks):
            case 0 if not self._all_finished:
                pass
            case 0 if self._all_finished and len(self._next_bundle_chunks) == 0:
                self._logger.debug(f'No more URLs, my work is done.')
                self.i_am_finished = True
            case _:
                self._celery_task.update_state(state='DNS CHECK')
                self._start_dns_check()
                self._check_urls_in_blacklists_or_service_not_known()
                self._evaluate_dns_check()
                self._check_bundles()
                self._sync_new_bundles_and_urls_with_db()
                self._celery_task.update_state(state='Start NEW CRAWLING TASKS')
                self._start_crawling_tasks()
        self._celery_task.update_state(state='IDEL', meta=self._build_state_meta())

    def _build_state_meta(self):
        meta = {}
        for group_observer in self._group_observer:
            if len(group_observer.group_tasks) > 0:
                task_states = []
                for group_task in group_observer.group_tasks:
                    task_states.extend([(result.id, AsyncResult(result.id, app=katti_app).state, AsyncResult(result.id, app=katti_app).info) for result in group_task.results])
                meta.update({'group': group_observer.group_id, 'task_states': task_states})
        return meta

    def _ready_for_new_urls(self):
        for group in self._group_observer:
            match group.group_state(self._db_obj.operation_group_modi):
                case 0:
                    pass
                case 2:
                    self._groups_ready_for_new_urls.append(group)
                case 3:
                    self._groups_ready_for_new_urls.append(group)
                    self._all_finished = True

    def _get_next_urls(self):
        if self._db_obj.spider_mode:
            self._get_urls_spider_mode()
        if self._db_obj.statefull_crawling:
            self._get_next_urls_with_statefull()
        else:
            self._get_next_urls_without_statefull()

    def _get_urls_spider_mode(self):
        for index, bundle_obj in enumerate(
                Bundle.objects(crawling_meta_data__crawling_request_id=self._db_obj.id, spider_track__preparation=True)):
            if index >= int((len(self._groups_ready_for_new_urls) * self._db_obj.max_urls_per_group) * self._db_obj.spider_mode.average_index):
                break
            bundle_obj.spider_track.preparation = False
            bundle_obj.katti_meta_data = Bundle.CrawlingMeta(crawling_config=self._db_obj.crawling_config)
            self._next_bundle_chunks.append([bundle_obj])

    def _get_next_urls_without_statefull(self):
        for url_for_crawling in URLForCrawling.objects(next_lookup__lte=datetime.datetime.utcnow(),
                                                       crawling_request_id=self._db_obj.id)[
                                :(len(self._groups_ready_for_new_urls) * self._db_obj.max_urls_per_group)]:
            self._url_crawling_obj_for_sync.append(url_for_crawling)
            self._build_bundle(url_for_crawling_set=url_for_crawling, statefull=False)

    def _get_next_urls_with_statefull(self):
        for url_for_crawling in URLForCrawling.objects(next_lookup__lte=datetime.datetime.utcnow(),
                                                       crawling_request_id=self._db_obj.id)[
                                :(len(self._groups_ready_for_new_urls) * self._db_obj.max_urls_per_group)]:
            self._url_crawling_obj_for_sync.append(url_for_crawling)
            self._build_bundle(url_for_crawling_set=url_for_crawling, statefull=True)

    def _build_bundle(self, url_for_crawling_set: URLForCrawling, statefull: bool=False):
        new_chunk = []
        for index, url in enumerate(url_for_crawling_set.urls):
            new_bundle = Bundle(id=ObjectId(),
                                crawling_url=URL.build(url),
                                crawling_meta_data=Bundle.CrawlingMeta(statefull_id=url_for_crawling_set.id if statefull else None,
                                                                       create=datetime.datetime.utcnow(),
                                                                       statefull_index=index if statefull else None,
                                                                       ownership=self._db_obj.ownership,
                                                                       katti_meta_data=self._db_obj.katti_meta_data,
                                                                       analyses_tracking=self._raw_analyses_tracking))
            headers = URLHeadersRedisCache(header_fields_all=url_for_crawling_set.all_header_fields, header_fields_regex=url_for_crawling_set.regex_headers)
            self._redis_cache.insert_http_headers_for_crawling(headers_cache=headers, bundle_id=new_bundle.id)
            self._bundles_for_sync.append(new_bundle)
            if not statefull:
                self._next_bundle_chunks.append([new_bundle])
            else:
                new_chunk.append(new_bundle)
        if len(new_chunk) > 0:
            self._next_bundle_chunks.append(new_chunk)

    def _check_urls_in_blacklists_or_service_not_known(self): #todo
        pass

    def _check_bundles(self):
        for chunk in self._next_bundle_chunks:
            x = []
            for bundle in chunk:
                if bundle.crawling_meta_data.blocked == 'no':
                    x.append(bundle)
                    continue
                if bundle.bundle.crawling_url.domain in self._nx_domains:
                    bundle.crawling_meta_data.blocked = 'nxdomain'
                    continue
                if bundle.bundle.crawling_url.domain in self._ip_blocked_domains:
                    bundle.crawling_meta_data.blocked = 'ip_blocked'
                    continue
            if len(x) > 0:
                self._add_chunk_to_group(x)

    def _start_dns_check(self):
        if not self._db_obj.dns_check:
            return
        self._dns_start_time = datetime.datetime.utcnow()
        domains = set()
        for bundle_list in self._next_bundle_chunks:
            for bundle in bundle_list:
                if '.onion' in bundle.crawling_url.domain: # No onion domains are checked.
                    continue
                domains.add(bundle.crawling_url.domain)
        self._start_dns_task([OOI(raw_ooi=domain, meta_data_obj=self._db_obj.katti_meta_data) for domain in domains])

    def _start_dns_task(self, prepared_domains):
        self._dns_task = group(dns_scanning_task.s(
            DomainsForDNSResolverRequest(oois=domain_chunk,
                                         scanner_id=self._crawling_config.dns_pre_check_scanner_id,
                                         time_valid_response=self._db_obj.dns_check_valid_time,
                                         ownership_obj=self._db_obj.ownership)) for domain_chunk in split(list(prepared_domains), chunk_size=5)).apply_async()

    def _evaluate_dns_check(self):
        if not self._dns_task:
            return
        try:
            start = datetime.datetime.utcnow()
            while (datetime.datetime.utcnow() - start).total_seconds() < 5:
                if self._dns_task.ready():
                    return self._proof_dns_result(self._dns_task.results)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))

    def _proof_dns_result(self, dns_result_objects: list[AsyncResult]):
        global BYPASS_DNS_PROOF
        if BYPASS_DNS_PROOF:
            return
        self._nx_domains = []
        self._ip_blocked_domains = []
        for result in dns_result_objects:
            match result.state:
                case ' SUCCESS':
                    for dns_result in result.get():
                        match dns_result.queries[-1].status:
                            case 'NXDOMAIN':
                                self._nx_domains.append(dns_result.ooi)
                            case 'NOERROR':
                                try:
                                    DNSResult.objects.only('id').get(Q(id=dns_result.queries[-1].dns_response) & (Q(A_record__ipaddress__exists=True) | Q(AAAA_record__ipaddress__exists=True)))
                                except DoesNotExist:
                                    self._nx_domains.append(dns_result.ooi)
                            case _:
                                pass

    def _ip_check_is_negative(self, dns_result) -> bool:
        return True

    def _add_chunk_to_group(self, bundle_chunk: list[Bundle]):
        crawling_groups = sorted(self._groups_ready_for_new_urls, key=lambda x: x.crawling_task_data_count, reverse=False)
        clones = crawling_groups[0].add_new_crawling_task(bundle_chunk=bundle_chunk,
                                                 request_id=self._db_obj.id,
                                                 random=self._db_obj.execute_urls_random,
                                                 statefull=self._db_obj.statefull_crawling,
                                                 crawling_config_id=self._db_obj.crawling_config.id)
        self._bundles_for_sync.extend(clones)

    def _start_crawling_tasks(self):
        for group in self._groups_ready_for_new_urls:
            group.start_crawling_tasks()

    def _sync_new_bundles_and_urls_with_db(self):
        if len(self._bundles_for_sync) > 0:
            Bundle.objects.insert(self._bundles_for_sync)
        if len(self._url_crawling_obj_for_sync) > 0:
            URLForCrawling()._get_collection().bulk_write([obj.set_lookup_and_cal_next() for obj in self._url_crawling_obj_for_sync])
