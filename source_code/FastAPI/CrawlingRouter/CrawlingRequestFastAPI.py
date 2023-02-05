from typing import Literal
from pydantic import BaseModel, HttpUrl, Field

class URLsForCrawling(BaseModel):
    pass

class CrawlingGroup(BaseModel):
    pass


class ExpertSettings(BaseModel):
    ignore_service_not_known_hours: int = Field(ge=0, default=24)
    ignore_blacklist_direct_match: bool = False
    ignore_blacklist_domain_match: bool = False
    dns_check: bool = False


    crawling_groups: list[CrawlingGroup]
    statefull_crawling: bool = False
    #i_dont_care_about_cookies: bool = True
    browser_privacy_level: Literal['max_data', 'privacy'] = 'max_data'


class WebbrowserConfig(BaseModel):
    browser_type: Literal['chrome', 'edge', 'firefox', 'chromium', 'undect_chrome']


class BrowserChoice(BaseModel):
    Chrome: bool = False
    Firefox: bool = False
    Edge: bool = False


class MultiBrowserURLS(BaseModel):
    urls: list[HttpUrl]
    analyses: list[str] #TODO Validation!!!
    tag_name: str | None = None
    browser: list[str]


class SingleURL(BaseModel):
    url: HttpUrl
    analyses: list[str] #TODO Validation!!!
    browser: list[str]
    tag_name: str | None

class ExperimentRequest(BaseModel):
    url_count: int
    browsers: list[str]
    analyses: list[str]
    tag_name: str | None


class CrawlingFastRequestResponse(BaseModel):
    crawling_request_id: str
    celery_task_id: str




