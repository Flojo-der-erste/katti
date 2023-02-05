import datetime
import os.path
import time
import uuid
from typing import Literal
from bson import ObjectId
from pydantic import HttpUrl
from starlette import status
from CeleryApps.CrawlingTasks import crawling_request_celery
from pymongo import InsertOne, ReturnDocument
from DataBaseStuff import FirefoxOptions
from DataBaseStuff.Helpers import save_mongoengine_objc_async, get_mongoengine_object_async, async_execute_bulk_ops, \
    get_async_cursor_bundle_for_crawling_request, async_update_mongoengine
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.URLForCrawling import URLForCrawling
from DataBaseStuff.MongoengineDocuments.Scanner.GoogleSafeBrwosingConfig import GoogleSafeBrowserConfig
from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import DNSExecutionInformation, \
    ShodanExecutionInformation, SSLScannerExecutionInformation, GSBExecutionInformation, VirusTotalExecutionInformation
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, Tag, MetaData
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import BrowserGroup, CrawlingRequest
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.ChromiumBasedOptions import ChromeOptions, \
    EdgeOptions, ChromiumOptions
from FastAPI.Dependencies import db
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import PreCrawlingAnalyseSettings, \
    AnalyseTask
from fastapi import APIRouter, HTTPException
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from FastAPI.CrawlingRouter.CrawlingRequestFastAPI import CrawlingFastRequestResponse, MultiBrowserURLS, SingleURL, \
    BrowserChoice, ExperimentRequest
from Scanner.VirusTotal.VirusTotal import VirusTotal

crawling_router = APIRouter(
    prefix="/api/crawling",
    tags=["Crawling"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


async def get_scanner(name):
    return await db['scanner'].find_one({'name': name})


@crawling_router.post("/execute_crawling_request/fast/one_browser_url", response_model=CrawlingFastRequestResponse)
async def execute_crawling_request(data: SingleURL):
    crawling_request = await build_and_start(analyses=data.analyses, browser=data.browser, urls=[data.url], tag_name=data.tag_name)
    task = crawling_request_celery.apply_async(args=(crawling_request.id,))
    return CrawlingFastRequestResponse(crawling_request_id=f'{crawling_request.id}', celery_task_id=str(task.id))


@crawling_router.post("/execute_crawling_request/fast/multi_browser_urls", response_model=CrawlingFastRequestResponse)
async def execute_crawling_request(data: MultiBrowserURLS):
    crawling_request = await build_and_start(analyses=data.analyses, browser=data.browser, urls=data.urls, tag_name=data.tag_name)
    task = crawling_request_celery.apply_async(args=(crawling_request.id,))
    return CrawlingFastRequestResponse(crawling_request_id=f'{crawling_request.id}', celery_task_id=str(task.id))


@crawling_router.post("/execute_crawling_request/experiment", response_model=CrawlingFastRequestResponse)
async def execute_crawling_request(data: ExperimentRequest):
    urls = []
    if len(data.browsers) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A browser... maybe')
    with open(os.path.expanduser('~/katti/source_code/Experiments/top-1m.csv'), 'r') as file:
        lines = file.readlines()
        for i in range(data.url_count):
            domain = lines[i].split(',')[-1]
            domain = domain.rstrip()
            urls.append(f'https://{domain}')
    crawling_request = await build_and_start(analyses=data.analyses, browser=data.browsers, urls=urls, tag_name=data.tag_name)
    task = crawling_request_celery.apply_async(args=(crawling_request.id,))
    return CrawlingFastRequestResponse(crawling_request_id=f'{crawling_request.id}', celery_task_id=str(task.id))


async def get_single_bundle_id(crawling_request_id: ObjectId) -> ObjectId:
    start_wait = datetime.datetime.utcnow()
    while (datetime.datetime.utcnow() - start_wait).seconds < 30:
        time.sleep(0.5)
        cursor = await get_async_cursor_bundle_for_crawling_request(db=db, crawling_request_id=crawling_request_id, projection={'_id': 1})
        async for bundle_id in cursor:
            return bundle_id['_id']
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Bad stuff...")


async def build_and_start(analyses, browser, urls: list[HttpUrl], tag_name: str | None=None) -> CrawlingRequest:
    time_lord = await db['time_lords'].find_one({'first_name': 'Dr. Who?'})
    if not time_lord:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='No default time lord :)')
    crawling_config = await get_mongoengine_object_async(CrawlingConfig, db=db,
                                                         collection_name=CrawlingConfig.collection_name(),
                                                         filter={'name': 'default_crawling'})
    if not crawling_config:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='No default crawling config')
    meta_data = MetaData()
    if tag_name:
        tag = await db['tags'].find_one_and_update(filter={'name': tag_name}, update={'$setOnInsert': {'create': datetime.datetime.utcnow(), 'ownership': {'owner': time_lord['_id']}}}, return_document=ReturnDocument.AFTER, upsert=True)
        meta_data = MetaData(tag=tag['_id'])


    google = await get_scanner('google') if 'google' in analyses else None
    quad = await get_scanner('quad9') if 'quad9' in analyses else None
    cloudflare = await get_scanner('cloudflare_security_malware') if 'cloudflare_security_malware' in analyses else None
    ssl = await get_scanner('ssl') if 'ssl' in analyses else None
    vt = await get_scanner('virustotal') if 'virustotal' in analyses else None
    gsb = await get_scanner('gsb') if 'gsb' in analyses else None
    after_analyses = PreCrawlingAnalyseSettings() if len(analyses) > 0 else None
    if google:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()), execution_information=DNSExecutionInformation(scanner_id=google['_id'], dig_type='ANY', time_valid_response=0)))
    if quad:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()),
                                                        execution_information=DNSExecutionInformation(
                                                            scanner_id=quad['_id'], dig_type='A')))
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()),
                                                        execution_information=DNSExecutionInformation(
                                                            scanner_id=quad['_id'], dig_type='AAAA')))
    if cloudflare:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()),
                                                        execution_information=DNSExecutionInformation(
                                                            scanner_id=cloudflare['_id'], dig_type='A')))
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()),
                                                        execution_information=DNSExecutionInformation(
                                                            scanner_id=cloudflare['_id'], dig_type='AAAA')))
    if ssl:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()), execution_information=SSLScannerExecutionInformation(scanner_id=ssl['_id'])))
    if vt:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()), execution_information=VirusTotalExecutionInformation(scanner_id=vt['_id'], endpoint=VirusTotal.VT_URL_ENDPOINT)))
    if gsb:
        after_analyses.analyse_tasks.append(AnalyseTask(task_id=str(uuid.uuid4()), execution_information=GSBExecutionInformation(scanner_id=gsb['_id'])))

    browser_configs = []
    if 'Chrome' in browser:
        browser_configs.append(await BrowserConfig.async_save_to_db(db, BrowserConfig.Config(browser_options=ChromeOptions())))
    if 'Edge' in browser:
        browser_configs.append(await BrowserConfig.async_save_to_db(db, BrowserConfig.Config(browser_options=EdgeOptions())))
    if 'Firefox' in browser:
        browser_configs.append(await BrowserConfig.async_save_to_db(db, BrowserConfig.Config(browser_options=FirefoxOptions())))
    if 'Chromium' in browser:
        browser_configs.append(await BrowserConfig.async_save_to_db(db, BrowserConfig.Config(browser_options=ChromiumOptions())))
    crawling_request = CrawlingRequest(ownership=Ownership(), crawling_config=crawling_config.id, analyses_settings=after_analyses, katti_meta_data=meta_data)
    crawling_request.crawling_groups = [BrowserGroup(browser_configs=[config.id for config in browser_configs])]
    await save_mongoengine_objc_async(db=db, mongoengine_obj=crawling_request, collection_name=CrawlingRequest.collection_name())
    bulk_ops = [InsertOne(URLForCrawling(urls=[url], crawling_request_id=crawling_request.id).to_mongo()) for url in urls]
    await async_execute_bulk_ops(db=db, bulk_ops=bulk_ops, force=True, min_ops=1, collection_name=URLForCrawling.collection_name())
    return crawling_request