from fastapi import APIRouter, Depends
from starlette.requests import Request
from FastAPI.APIModels.SannityCheckModels.SannityCheckRequestModel import SannityCheckRequestModel, \
    SannityCheckResponseModel
from FastAPI.Dependencies import api_login
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord

sannity_router = APIRouter(
    prefix="/api/scanner",
    tags=["SannityCheck"],
   # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@sannity_router.get("/sanitycheck/", response_model=SannityCheckResponseModel)
async def sannity_check(data: SannityCheckRequestModel, request: Request, user: TimeLord = Depends(api_login)):
   return await sanitycheck_request()


async def sanitycheck_request():
    pass