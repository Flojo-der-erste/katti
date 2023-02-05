import datetime
import io
import ipaddress
import os
import re
import time
from urllib.parse import urlparse
import dhash
import yaml
from PIL import Image


def split(list_a, chunk_size):
  for i in range(0, len(list_a), chunk_size):
    yield list_a[i:i + chunk_size]


def sleep(how_long, stop_event):
    start = datetime.datetime.now()
    while (datetime.datetime.now() - start <= how_long and how_long > 0) and not stop_event.is_set():
        time.sleep(1)


def isValidDomain(domain: str):
    """https://www.geeksforgeeks.org/how-to-validate-a-domain-name-using-regular-expression/"""
    regex = "^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.)+[A-Za-z]{2,6}"
    p = re.compile(regex)
    if (domain == None):
        return False
    if (re.search(p, domain)):
        return True
    else:
        return False

def is_ip_addr_valid(ip_addr: str):
    try:
        ip = ipaddress.ip_address(ip_addr)
    except Exception:
        return False
    else:
        return True


def is_valid_url(url: str) -> bool:
    o = urlparse(url)
    return True #if o.scheme and o.netloc else False


def convert_micro_timestamp_to_datetime(timestamp: int) -> datetime.datetime | None:
    if not timestamp:
        return None
    try:
        datetim_e = datetime.datetime.fromtimestamp(timestamp / 1000)
    except Exception:
        return None
    else:
        return datetim_e



def calculate_dhash(raw_pic, pic_id):
    image = Image.open(io.BytesIO(raw_pic))
    return dhash.dhash_row_col(image)
