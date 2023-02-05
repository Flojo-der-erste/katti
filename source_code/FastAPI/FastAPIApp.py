from fastapi import FastAPI
from FastAPI.CrawlingRouter.Routes import crawling_router
from FastAPI.ScannerRouter.Routes import scanner_router
from RedisCacheLayer.RedisMongoCache import RedisMongoCache

meta = {'meta': {
  'title': "Katti's amazing API",
  'description': "Katti helps you do awesome stuff. 🚀",
  'contact':{
    'name': "Dr. Who",
    'email': "drwho@gallifrey.com"}}}


redis_mongo_cache = RedisMongoCache()

app = FastAPI(**meta)
app.include_router(scanner_router)
app.include_router(crawling_router)








