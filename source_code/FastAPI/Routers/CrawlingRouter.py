from fastapi import APIRouter
from FastAPI.APIModels.CrawlingModels.CrawlingRequestResponseModel import CrawlingRequestResponseModel, \
    CrawlingRequestModel

crawling_router = APIRouter(
    prefix="/crawling/",
    tags=["Crawling"],
   # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@crawling_router.get("/new_request/", response_model=CrawlingRequestResponseModel)
async def new_crawling_request(data: CrawlingRequestModel):
   pass



