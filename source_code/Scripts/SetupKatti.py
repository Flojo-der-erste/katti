import datetime
import os
from argparse import ArgumentParser
from typing import Type
import yaml
from mongoengine import get_db

from DataBaseStuff.MongoengineDocuments.Crawling.BrowserAndExtension import Browser
from pymongo import UpdateOne
from DataBaseStuff.ConnectDisconnect import connect_to_database
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest
from DataBaseStuff.MongoengineDocuments.Crawling.DatabaseHTTPRequest import DatabaseHTTPRequest
from DataBaseStuff.MongoengineDocuments.Crawling.HTTPRequestHeader import UserAgentString
from DataBaseStuff.MongoengineDocuments.Crawling.NeighborhoodMatrix import MatrixCell
from DataBaseStuff.MongoengineDocuments.Crawling.OutsourcedData import OutsourcedData
from DataBaseStuff.MongoengineDocuments.Crawling.URLForCrawling import URLForCrawling
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.MalwareFamilyMapping import MalwareFamilyMapping
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScannerDocument
from DataBaseStuff.MongoengineDocuments.Scanner.TracerouteConfig import TracerouteConfig
from DataBaseStuff.MongoengineDocuments.Scanner.Shodan import ShodanScannerDB
from DataBaseStuff.MongoengineDocuments.Scanner.VirusTotalConfig import VirusTotalConfig
from DataBaseStuff.MongoengineDocuments.Scanner.SSLScanner import SSLScannerDB
from DataBaseStuff.MongoengineDocuments.Scanner.FarsightDocument import FarsightDocument
from DataBaseStuff.MongoengineDocuments.Scanner.DNSServerConfig import DNSConfig
from DataBaseStuff.MongoengineDocuments.Scanner.GoogleSafeBrwosingConfig import GoogleSafeBrowserConfig
from DataBaseStuff.MongoengineDocuments.UserManagement.TimeLord import TimeLord
from Utils.UpdateUserAgentStrings import update_strings


scanner = {'dns': ['dns_config', DNSConfig],
           'dnsbl': ['dnsbl_config', DNSConfig],
         #  'farsight': ['farsight_config', FarsightDocument],
           'gsb': ['gsb_config', GoogleSafeBrowserConfig],
           'ssl': ['ssl_scanner_config', SSLScannerDB],
           'vt': ['vt_config', VirusTotalConfig],
           'shodan': ['shodan_config', ShodanScannerDB],
           'traceroute': ['traceroute_config', TracerouteConfig]}


def args():
    parser = ArgumentParser()
    parser.add_argument('-up_sca', dest='update_scanners', default=True)
    parser.add_argument('-in_def_u', dest='insert_default_user', default=True)
    parser.add_argument('-up_ua_str', dest='update_ua_strings', default=True)
    return parser.parse_args()


def insert_function_for_scanner(scanner_db_cls: Type[BaseScannerDocument], yml_name: str):
    bulk_ops = []
    scanner_db_cls.ensure_indexes()


    with open(os.path.join(os.path.expanduser('~/katti/config'), f'Scanner/{yml_name}.yml'), 'r') as raw_file:
        config_file = yaml.safe_load(raw_file)
        for scanner_name in config_file['scanner']:
            print(f'Scanner name: {scanner_name}, type: {config_file["scanner_type"]}')
            if config_file['scanner'][scanner_name] and 'api_key' in config_file['scanner'][scanner_name] and config_file['scanner'][scanner_name]['api_key'] == 'your_api_key':
                continue
            new_scanner = scanner_db_cls(name=scanner_name, type=config_file['scanner_type'],
                                         **config_file['scanner'][scanner_name] if config_file['scanner'][scanner_name] else {})
            new_scanner.validate(clean=True)
            bulk_ops.append(UpdateOne({'name': scanner_name}, {'$set': new_scanner.to_mongo()}, upsert=True))

    if len(bulk_ops) > 0:
        scanner_db_cls()._get_collection().bulk_write(bulk_ops, ordered=False)


def prepare_database(args):
    browsers = [Browser(name='Chrome', version='latest'), Browser(name='Edge', version='latest'), Browser(name='Firefox', version='latest'), Browser(name='Chromium', version='latest')]
    Browser.objects.insert(browsers)
    db = get_db('Katti')
    db.create_collection('bundles_with_requests',
                         viewOn='bundles',
                         pipeline=[
                             {
                                 '$lookup': {
                                     'from': 'requests',
                                     'localField': 'requests',
                                     'foreignField': '_id',
                                     'as': 'requests'
                                 }
                             }
                         ])
    documents_for_indexes_creation = [Bundle, CrawlingRequest, DatabaseHTTPRequest, UserAgentString, MatrixCell,
                                      OutsourcedData, URLForCrawling, BrowserConfig, BaseScannerDocument, TimeLord,
                                      MalwareFamilyMapping]

    default_crawling_configuration = CrawlingConfig(name='default_crawling', dns_pre_check_scanner_id=DNSConfig.objects.get(name='google').id)
    default_crawling_configuration.save()
    for mongoengine_cls in documents_for_indexes_creation:
        mongoengine_cls.ensure_indexes()
    if args.insert_default_user:
        default_user = TimeLord(first_name='Dr. Who?',
                                last_name='The Dr.',
                                department='TARDIS Dep. 1',
                                email='drwho@gallifrey.42',
                                pw_hash='Dalek',
                                created=datetime.datetime.utcnow())
        default_user.save()
    if args.update_ua_strings:
        update_strings()



if __name__ == '__main__':
    connect_to_database()
    arg = args()
    if arg.update_scanners:
        for type in scanner:
            insert_function_for_scanner(scanner_db_cls=scanner[type][1], yml_name=scanner[type][0])
    prepare_database(arg)
