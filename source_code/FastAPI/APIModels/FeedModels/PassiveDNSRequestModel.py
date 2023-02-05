from pydantic import BaseModel
from pydantic.json import IPv4Address, IPv6Address

from FastAPI.APIModels.GenericModels.FeedGenericRequestModel import FeedGenericRequestModel


class PassiveDNSRequestModel(FeedGenericRequestModel):
    domains: list[str] | None = None

    ips_v4: list[IPv4Address] | None = None
    ips_v6: list[IPv6Address] | None = None

    types: list[str] | None = None


class PassiveDNSDomainEntry(BaseModel):
    domain: str


class PassiveDNSNXDomainEntry(BaseModel):
    domain: str


class PassiveDNSCnameEntry(BaseModel):
    domain: str
    cname: str


class PassiveDNSIPv4Entry(BaseModel):
    domain: str
    ipv4: IPv4Address


class PassiveDNSIPv6Entry(BaseModel):
    domain: str
    ipv6: IPv6Address


class PassiveDNSResponseModel(BaseModel):
    skip: int
    limit: int
    domain: list[PassiveDNSDomainEntry] | None = []
    nxdomain: list[PassiveDNSNXDomainEntry] | None = []
    cname: list[PassiveDNSCnameEntry] | None = []
    ipv4: list[PassiveDNSIPv4Entry] | None = []
    ipv6: list[PassiveDNSIPv6Entry] | None = []