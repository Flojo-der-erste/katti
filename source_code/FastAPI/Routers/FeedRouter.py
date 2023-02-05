import motor.motor_asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.requests import Request
from FastAPI.APIModels.FeedModels.BitsightFeedRequestModel import BitsightFeedRequestModel, BitsightFeedResponseModel
from FastAPI.APIModels.FeedModels.DGAFeedRequestModel import DGAFeedResponseModel, DGAFeedRequestModel, FkieFeedEntry
from FastAPI.APIModels.FeedModels.PassiveDNSRequestModel import PassiveDNSRequestModel, PassiveDNSResponseModel
from FastAPI.APIModels.FeedModels.RSSFeedRequestModel import RSSFeedModel, RSSFeedResponseModel
from FastAPI.APIModels.FeedModels.SinkDBFeedModels import SinkDBFeed, SinkDBResponseModel
from FastAPI.APIModels.FeedModels.TorFeedRequestResponseModels import TorFeedModel, TorFeedResponseModel
from FastAPI.APIModels.FeedModels.TrancoFeedRequestModel import TrancoFeedRequestModel, TrancoFeedResponseModel
from FastAPI.Dependencies import api_login
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord

feed_router = APIRouter(
    prefix="/api/feed",
    tags=["Feeds"],
   # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

class Cars(BaseModel):
    model: str = 'test'
    farbe: str = 'blau'


@feed_router.get("/test/", response_model=list[Cars])
async def test():
   return [Cars() for i in range(100)]

@feed_router.get("/tranco/", response_model=TrancoFeedResponseModel)
async def get_tranco_data(data: TrancoFeedRequestModel, request: Request, user: TimeLord = Depends(api_login), test:str = 'hahah'):
   return await new_feed_api_request(endpoint='tranco', user=user, request=data.dict())


@feed_router.get("/rss/", response_model=RSSFeedResponseModel)
async def get_rss_data(data: RSSFeedModel, request: Request, user: TimeLord = Depends(api_login)):
    return await new_feed_api_request(endpoint='rss', user=user, request=data.dict())


@feed_router.get("/dga/", response_model=DGAFeedResponseModel)
async def get_dga_data(request: DGAFeedRequestModel):
    return await new_feed_api_request(endpoint='dga', request=request)


@feed_router.get("/passive_dns/", response_model=PassiveDNSResponseModel)
async def get_passive_dns_data(data: PassiveDNSRequestModel, request: Request, user: TimeLord = Depends(api_login)):
    return await new_feed_api_request(endpoint='dga', user=user, request=data)


@feed_router.get("/bitsight/", response_model=BitsightFeedResponseModel)
async def get_bitsightdata(data: BitsightFeedRequestModel, request: Request, user: TimeLord = Depends(api_login)):
    return await new_feed_api_request(endpoint='dga', user=user, request=data.dict())


@feed_router.get("/tor/", response_model=TorFeedResponseModel)
async def get_tor_data(data: TorFeedModel, request: Request, user: TimeLord = Depends(api_login)):
    return await new_feed_api_request(endpoint='dga', user=user, request=data.dict())


@feed_router.get("/sinkdb/", response_model=SinkDBResponseModel)
async def get_sinkdb_data(data: SinkDBFeed, request: Request, user: TimeLord = Depends(api_login)) -> PassiveDNSResponseModel:
    return await new_feed_api_request(endpoint='dga', user=user, request=data.dict())


async def new_feed_api_request(endpoint: str, request):
    # new_stats = FastAPIStats(start_time=datetime.datetime.utcnow(), user=user, request=request.dict(), endpoint=f'/api/feed/{endpoint}')
    #check_authorization_and_rate_limit(user, endpoint)
   # celery_task = api_feed_request.apply_async((request.dict(), endpoint, f'{user.id}'))
    #result = await wait_for_task(task_id=celery_task.id, task=api_feed_request)
    client: motor.motor_asyncio.AsyncIOMotorClient = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['Feeds']
    print(db)
    cursor = db['dga_entries'].aggregate(request.db_filter())
    print(cursor)
    response = DGAFeedResponseModel(limit=request.limit, skip=request.skip)
    async for doc in cursor:
        match doc['_cls']:
            case 'BaseDGAEntry.FKIEFeedEntry':
                response.fkie_entries.append(FkieFeedEntry.build_from_db_doc(doc))

    #new_stats.stop_time = datetime.datetime.utcnow()
    #new_stats.run_time_ms = (new_stats.stop_time - new_stats.start_time).microseconds

    return response