from typing import Literal
from FastAPI.APIModels.GenericModels.GenericScannerResponseRequest import GenericScannerResponse
from FastAPI.APIModels.ScannerModels.ShodanModels import ShodanAPIExecuteRequest
from Scanner.GSB.GoogleSafeBrowsing import URLsForGSBRequest
from FastAPI.APIModels.ScannerModels.FastAPIModels import FarsightRequestRawRequest, FrasightRequestQuery
from FastAPI.APIModels.ScannerModels.GSBModels import GSBRequest
from FastAPI.APIModels.ScannerModels.SSLScanner import SSLScannerRequest
from celery import group
from celery.result import AsyncResult, GroupResult
from pydantic.typing import List
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData
from DataBaseStuff.Piplines import get_complete_dns_request
from FastAPI.APIModels.ScannerModels.VirusTotalModels import VirusTotalRequest, EndpointResponse
from Scanner.BaseScanner import OOI
from Scanner.DNS.DNSResolver import DomainsForDNSResolverRequest
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from CeleryApps.ScanningTasks import dns_scanning_task, ssl_scanning_task, farsight_scanning_task, vt_scanning_task, \
    gsb_scanning_task
from FastAPI.APIModels.ScannerModels.DNSModels import DNSScanner, DNSScannerRequest, IPCheckDNSRequest
from FastAPI.Dependencies import db
from Scanner.Farsight.Farsight import FarsightQuerries, FarsightOOI
from Scanner.SSLScanner.SSLScanner import DomainsIPsForSSLScanning
from Scanner.VirusTotal.VirusTotal import IOCsForVTRequest

scanner_router = APIRouter(
    prefix="/api/scanner",
    tags=["Scanners"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@scanner_router.post("/get_scanner", response_model=List[DNSScanner])
async def get_scanner(all: bool = True, dns: bool = True, ssl: bool = True, farsight: bool = True, gsb: bool = True,
                      vt: bool = True, active: bool = False, not_active: bool = False):
    if all:
        _cls_list = ['BaseScannerDocument.DNSConfig', 'BaseScannerDocument.FarsightDocument',
                     'BaseScannerDocument.VirusTotalConfig', 'BaseScannerDocument.SSLScanner']
    else:
        _cls_list = []
        if dns:
            _cls_list.append('BaseScannerDocument.DNSConfig')
        if ssl:
            _cls_list.append('BaseScannerDocument.SSLScanner')
        if farsight:
            _cls_list.append('BaseScannerDocument.FarsightDocument')
        if vt:
            _cls_list.append('BaseScannerDocument.VirusTotalConfig')
    query = {'_cls': {'$in': _cls_list}}
    if active and not not_active:
        query.update({'active': True})
    if not active and not_active:
        query.update({'active': False})
    return [DNSScanner.build_from_raw_db_answer(x) async for x in db['scanner'].find(query)]


@scanner_router.post("/dns/real/execute_dns", response_model=GenericScannerResponse)
async def execute_dns_request(data: DNSScannerRequest, request: Request):
    return await execute_dns(data)


@scanner_router.post("/dns/ip_check/execute_dns", response_model=GenericScannerResponse)
async def execute_dns_request(data: IPCheckDNSRequest, request: Request):
    return await execute_dns(data)


@scanner_router.post("/ssl/execute_ssl", response_model=GenericScannerResponse)
async def execute_ssl_request(data: SSLScannerRequest, request: Request):
    meta_data, oois = await prepare_request(data, 'domains')
    ssl_task = ssl_scanning_task.s(
        build_celery_scanning_request(DomainsIPsForSSLScanning, meta_data, oois, data.ssl_scanner_id,
                                      data)).apply_async()
    task_result: GroupResult = await wait_for_celery_task(task=ssl_task, max_wait_time=5000)
    return_results = GenericScannerResponse()
    for single_result in task_result.results:
        return_results.results.append(single_result.to_mongo())
    return return_results


@scanner_router.post("/farsight/execute_api_call", response_model=GenericScannerResponse)
async def execute_farsight_request(data: FarsightRequestRawRequest, request: Request):
    meta_data, oois = await prepare_request(data, 'oois')
    return await execute_farsight(meta_data, oois, data)


@scanner_router.post("/farsight/execute_api_call_with_query", response_model=GenericScannerResponse)
async def execute_farsight_query(data: FrasightRequestQuery):
    await data.validate_db_fields(db)
    meta_data = None
    if data.tag_id:
        meta_data = MetaData(tag=ObjectId(data.tag_id))
    oois = [FarsightOOI(raw_ooi=x, raw_query=True) for x in data.raw_querries]
    return await execute_farsight(meta_data, oois, data)


@scanner_router.post("/virus_total/execute_api_call", response_model=GenericScannerResponse)
async def execute_virus_total_api_call(data: VirusTotalRequest):
    scanner_id = await get_default_scanner_id(name='virus_total') if not data.scanner_id else data.scanner_id
    meta_data, oois = await prepare_request(data, 'oois')
    return await wait_for_celery_task(task=vt_scanning_task.s(
        build_celery_scanning_request(IOCsForVTRequest,
                                      meta_data,
                                      oois,
                                      scanner_id,
                                      data)).apply_async(), max_wait_time=30)


@scanner_router.get("/virus_total/get_endpoints", response_model=EndpointResponse)
async def get_virus_total_endpoints():
    return EndpointResponse()


@scanner_router.get("/google_safe_browsing/execute_api_call", response_model=EndpointResponse)
async def execute_gsb_api_call(data: GSBRequest):
    scanner_id = await get_default_scanner_id(name='gsb') if not data.scanner_id else data.scanner_id
    meta_data, oois = await prepare_request(data, 'urls')
    return await wait_for_celery_task(task=gsb_scanning_task.s(
        build_celery_scanning_request(URLsForGSBRequest,
                                      meta_data,
                                      oois,
                                      scanner_id,
                                      data)).apply_async(), max_wait_time=30)


@scanner_router.get("/shodan/execute_api_call", response_model=EndpointResponse)
async def execute_shodan_api_call(data: ShodanAPIExecuteRequest):
    scanner_id = await get_default_scanner_id(name='gsb') if not data.scanner_id else data.scanner_id
    meta_data, oois = await prepare_request(data, 'urls')
    return await wait_for_celery_task(task=gsb_scanning_task.s(
        build_celery_scanning_request(URLsForGSBRequest,
                                      meta_data,
                                      oois,
                                      scanner_id,
                                      data)).apply_async(), max_wait_time=30)


@scanner_router.get("/sub_results/{type}")
async def get_sub_results(id: str, type: Literal['farsight'] = 'farsight'):
    pass


async def get_default_scanner_id(name: str) -> ObjectId:
    scanner_result = await db['scanner'].find_one({'name': name, 'active': True})
    if not scanner_result:
        raise HTTPException(status_code=501, detail=f'Scanner {name} not available')
    return scanner_result['_id']


def build_celery_scanning_request(request_cls, meta_data_objc, oois, scanner_id, request_data):
    return request_cls(oois=oois,
                       scanner_id=scanner_id,
                       force=request_data.force,
                       ownership_obj=Ownership(),
                       time_valid_response=request_data.valid_result,
                       meta_data_obj=meta_data_objc,
                       **request_data.get_dict_for_celery_request())


async def prepare_request(request_data, oois_attribute):
    await request_data.validate_db_fields(db)
    meta_data = None
    if request_data.tag_id:
        meta_data = MetaData(tag=ObjectId(request_data.tag_id))
    oois = [OOI(raw_ooi=x, meta_data_obj=meta_data) for x in getattr(request_data, oois_attribute)]
    return meta_data, oois


async def wait_for_celery_task(task: AsyncResult, max_wait_time) -> GroupResult:
    try:
        result = task.get(timeout=max_wait_time, interval=0.3)
    except TimeoutError:
        raise HTTPException(status_code=501, detail='DNS, timeout')
    except Exception as e:
        print(e)
        raise HTTPException(status_code=501, detail='Bad stuff')
    else:
        if task.failed():
            raise HTTPException(status_code=501, detail='Task not success state')
        else:
            return result


async def execute_farsight(meta_data, oois, data, max_wait=30):
    farsight_scanner_id = await get_default_scanner_id('farsight') if not data.scanner_id else data.scanner_id
    farsight_task_result = await wait_for_celery_task(task=farsight_scanning_task.s(
        build_celery_scanning_request(FarsightQuerries, meta_data, oois, farsight_scanner_id, data)).apply_async(),
                                                      max_wait_time=30)
    return_results = GenericScannerResponse()
    for single_result in farsight_task_result.results:
        return_results.results.append(single_result.to_mongo())
    return return_results


async def execute_dns(data):
    if isinstance(data, DNSScannerRequest):
        meta_data, oois = await prepare_request(data, 'domains')
    else:
        meta_data, oois = await prepare_request(data, 'ipv4')
    dns_task = group(dns_scanning_task.s(
        build_celery_scanning_request(DomainsForDNSResolverRequest, meta_data, oois, scanner_id, data)) for scanner_id
                     in data.dns_scanner_ids).apply_async()
    group_task_result: GroupResult = await wait_for_celery_task(task=dns_task, max_wait_time=10)
    return_results = GenericScannerResponse()
    for single_result in group_task_result:
        async for db_result in db['dns_request'].aggregate(
                get_complete_dns_request([dns_request.id for dns_request in single_result.results])):
            return_results.results.append(db_result)
    return return_results
