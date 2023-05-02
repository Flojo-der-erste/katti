from ipaddress import IPv4Address
from typing_extensions import dataclass_transform


def parse_soa_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'mname': data_split[0],
            'rname': data_split[1],
            'serial': int(data_split[2]),
            'update': int(data_split[3]),
            'retry': int(data_split[4]),
            'expire': int(data_split[5])}


def parse_a_record(rdata: str) -> dict:
    return {'ipaddress': rdata, 'ip_int': int(IPv4Address(rdata))}


def parse_aaaa_record(rdata: str) -> dict:
    return {'ipaddress': rdata}


def parse_ns_record(rdata: str) -> dict:
    return {'target': rdata}


def parse_dns_key_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'algorithms_flag': int(data_split[0]),
            'protocol': int(data_split[1]),
            'algorithms_id': int(data_split[2]),
            'key': data_split[3]}


def parse_txt_record(rdata: str) -> dict:
    return {'text': rdata}


def parse_ds_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'key_tag': int(data_split[0]),
            'algorithm': int(data_split[1]),
            'digest_type': int(data_split[2]),
            'digest': data_split[3]}


def parse_mx_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'priority': data_split[0],
            'mail_host': data_split[1]}

def parse_caa_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'flag': data_split[0],
            'tag': data_split[1],
            'value': data_split[2]}

def parse_cname_record(rdata: str) -> dict:
    return {'cname': rdata}

def parse_ptr_record(rdata: str) -> dict:
    return {'target': rdata}

def parse_srv_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'priority': int(data_split[0]),
            'weight': int(data_split[1]),
            'port': data_split[2],
            'target': data_split[3]}

def parse_tlsa_record(rdata: str) -> dict:
    data_split = rdata.split(' ')
    return {'host': data_split[0],
            'usage': data_split[1],
            'selector': bool(data_split[2]),
            'matching_type': data_split[3],
            'hash': data_split[4]}


