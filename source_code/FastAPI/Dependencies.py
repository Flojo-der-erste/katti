import datetime
import threading
import validators
from DataBaseStuff.MongoengineDocuments.UserManagement import TimeLord
from bson import ObjectId
from bson.errors import InvalidId
from celery import Task
from celery.result import AsyncResult, GroupResult
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from starlette import status
import motor.motor_asyncio
from passlib.context import CryptContext
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from Utils.ConfigurationClass import FastAPIConfig, DatabaseConfigs
from validators import ValidationFailure as ValidatorsValidationFailure

CFG = DatabaseConfigs.get_config()
client: motor.motor_asyncio.AsyncIOMotorClient = motor.motor_asyncio.AsyncIOMotorClient(CFG.get_mongodb_uri_for_user())
db = client['Katti']


security = HTTPBasic()
lock = threading.Lock()
fastapi_config = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_fastapi_config() -> FastAPIConfig:
    global fastapi_config, lock
    with lock:
        if not fastapi_config:
            fastapi_config = FastAPIConfig.get_config()
        return fastapi_config


async def api_login(credentials: HTTPBasicCredentials = Depends(security)):
    redis_cache: RedisMongoCache = RedisMongoCache()
    try:
        katti_user = await redis_cache.get_mongoengine_cache_async(mongo_motor=db, cache_key=f'{credentials.password}_{credentials.username}', mongoengine_cls=TimeLord, mongo_filter={'email': credentials.username, 'api.key': credentials.password, 'user_is_active': True}, ttl=2*60)
        if not katti_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect ID or api key",
                headers={"WWW-Authenticate": "Basic"})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID or api key",
            headers={"WWW-Authenticate": "Basic"})
    else:
        return katti_user


def check_authorization_and_rate_limit(katti_user, api_endpoint):
    match katti_user.api.has_acess(api_endpoint):
        case 100:
            raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No access",
                    headers={"WWW-Authenticate": "Basic"})
        case 200:
            raise HTTPException(
                    status_code=402,
                    detail="Rate limit",
                    headers={"WWW-Authenticate": "Basic"})
        case _:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No access",
                headers={"WWW-Authenticate": "Basic"})


async def wait_for_task(task_id, task: Task):
    start = datetime.datetime.utcnow()
    result = None
    while (datetime.datetime.utcnow() - start).total_seconds() <= get_fastapi_config().celery_wait_timeout_s:
        try:
            result = task.AsyncResult(task_id).get(0.005)
        except Exception:
            pass
    if not result or result['traceback']:
        raise HTTPException(
            status_code=505,
            detail="Contact Admin",
            headers={'x-task-id': f'{task_id}'})
    return result


def check_domain(domain):
    if isinstance(validators.domain(domain), ValidatorsValidationFailure):
        return False
    return True


class FastAPIObjectID(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        try:
            return cls(v)
        except InvalidId:
            raise ValueError("Not a valid ObjectId")


    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string", example='')


async def wait_for_celery_task(task: AsyncResult, max_wait_time) -> GroupResult | AsyncResult:
    try:
        result = task.get(timeout=max_wait_time, interval=0.1)
    except TimeoutError:
        raise HTTPException(status_code=501, detail='Task timeout.')
    except Exception as e:
        print(e)
        raise HTTPException(status_code=501, detail='Bad stuff')
    else:
        if task.failed():
            raise HTTPException(status_code=501, detail='Task not success state')
        else:
            return result


