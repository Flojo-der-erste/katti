import datetime
import time
import unittest
import uuid
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.FirefoxOptions import FirefoxOptions
from DataBaseStuff.MongoengineDocuments.Scanner.DNSServerConfig import DNSConfig
from DataBaseStuff.MongoengineDocuments.Scanner.GoogleSafeBrwosingConfig import GoogleSafeBrowserConfig
from bson import ObjectId
from CeleryApps.CrawlingTasks import crawling_request_celery
from DataBaseStuff.ConnectDisconnect import connect_to_database
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from DataBaseStuff.MongoengineDocuments.Crawling.CrawlinRequest import CrawlingRequest, BrowserGroup
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import PreCrawlingAnalyseSettings, \
    AnalyseTask
from DataBaseStuff.MongoengineDocuments.Crawling.URLForCrawling import URLForCrawling
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.BrowserConfig import BrowserConfig
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.ChromiumBasedOptions import ChromeOptions, \
    EdgeOptions
from DataBaseStuff.MongoengineDocuments.ScannerExecutionInformation import DNSExecutionInformation, \
    GSBExecutionInformation
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership, MetaData, Tag


class TestStringMethods(unittest.TestCase):

    def setUp(self):
        connect_to_database()
        self.after_anal = PreCrawlingAnalyseSettings()
        try:
            self.after_anal.analyse_tasks.append(
                AnalyseTask(task_id=str(uuid.uuid4()), execution_information=DNSExecutionInformation(scanner_id=DNSConfig.objects.get(name='google').id, dig_type='ANY')))
        except Exception:
            print('google not in db')
        try:
            self.after_anal.analyse_tasks.append(
                AnalyseTask(task_id=str(uuid.uuid4()), execution_information=DNSExecutionInformation(scanner_id=DNSConfig.objects.get(name='quad9d').id, dig_type='A')))
        except Exception:
            print('quad not in db')
        try:
            self.after_anal.analyse_tasks.append(
                AnalyseTask(task_id=str(uuid.uuid4()), execution_information=DNSExecutionInformation(scanner_id=DNSConfig.objects.get(name='cloudflare_security_malware').id, dig_type='ANY')))
        except Exception:
            print('Cloudflare not in db')
        try:
            self.after_anal.analyse_tasks.append(
                AnalyseTask(task_id=str(uuid.uuid4()), execution_information=GSBExecutionInformation(scanner_id=GoogleSafeBrowserConfig.objects.get(name='gsb').id)))
        except Exception:
            print('GSB not in db')


      #  try:
      #      pass
           # self.after_anal.scanning_tasks.append(ScanningTask(scanning_type='ssl', ooi_kind='domain', scanner_id=SSLScannerDB.objects.get(name='ssl_scanner').id, max_analysis=0))
      #  except Exception:
      #      print('ssl scanner not in db')
      #  try:
      #      self.after_anal.scanning_tasks.append(ScanningTask(scanning_type='shodan', ooi_kind='ip', scanner_id=ShodanScannerDB.objects.get(name='shodan').id, max_analysis=0, time_valid_response=3600))
      #  except Exception:
       #     print('shodan not in db')
#www.bsi.bund.de

    def test_experiment(self):
        """ 1. One Crawling VM (chrome)
          2.  Two crawling VMs (chrome)
          3. Three crawling VMs (chrome)
          4. One Crawling VM (chrome, edge)
          5. ..
          6. ..
          7. One Crawling VM (edeg, chrome,firefox)
          9. Three Crawling VMs (..)"""
        start = datetime.datetime.utcnow()
        browser_config = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=ChromeOptions(use_tor=False), workflow='', simulating_user_actions=False))
        #browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions(use_tor=False)))
        #browser_config_3 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=FirefoxOptions(use_tor=False)))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        #browser_group.browser_configs.append(browser_config_2.id)
        #browser_group.browser_configs.append(browser_config_3.id)
        ownership = Ownership()

        crawling_config = CrawlingConfig.objects.get(name='default_crawling')
        tag = Tag(name='Experiment 9', create=datetime.datetime.utcnow(), owner=ownership)
        tag.save()
        meta = MetaData(tag=tag.id)
        crawling_r = CrawlingRequest(id=ObjectId(), ownership=ownership, crawling_config=crawling_config, statefull_crawling=False, operation_group_modi='not_waiting', dns_check_valid_time=0, katti_meta_data=meta)
       # crawling_r.analyses_settings = self.after_anal
        crawling_r.infinity_run = False
        crawling_r.crawling_groups.append(browser_group)
        crawling_r.save()
        with open('../../Experiments/top-1m.csv', 'r') as file:
            lines = file.readlines()
            for i in range(1000):
                url = URLForCrawling()
                url.max_lookups = 1
               # url.interval = interval
                url.crawling_request_id = crawling_r
                domain = lines[i].split(',')[-1]
                domain = domain.rstrip()
                url.urls.append(f'https://reddit.com')
                url.save()

        task = crawling_request_celery.apply_async(args=(crawling_r.id,))
        while not task.ready():
            print(f'{datetime.datetime.utcnow()} still running {task.id}')
            time.sleep(1)
        end = datetime.datetime.utcnow()
        print(f'Time: {end - start}')

    def test_chrome(self):
        browser_config = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=FirefoxOptions(use_tor=False)))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)

        crawling_config = CrawlingConfig.objects.get(name='default_crawling')
        meta = MetaData(das_is_ein_test='hahah')
        crawling_r = CrawlingRequest(id=ObjectId(), ownership=Ownership(), crawling_config=crawling_config, statefull_crawling=True, operation_group_modi='waiting', dns_check_valid_time=0, katti_meta_data=meta)
        crawling_r.analyses_settings = self.after_anal
        crawling_r.infinity_run = False
        crawling_r.crawling_groups.append(browser_group)
        crawling_r.save()
       # interval = Interval()
       # interval.every = 10
       # interval.period = 'seconds'
        with open('../../Experiments/top-1m.csv', 'r') as file:
            lines = file.readlines()
            for i in range(1):
                url = URLForCrawling()
                url.max_lookups = 1
               # url.interval = interval
                url.crawling_request_id = crawling_r
                domain = lines[i].split(',')[-1]
                domain = domain.rstrip()
                url.urls.append(f'https://www.via-verde-reisen.de/')
                print(lines[i])

                url.save()

        task = crawling_request_celery.apply_async(args=(crawling_r.id,))
        while not task.state == 'SUCCESS':
            print(f'{datetime.datetime.utcnow()} {task.state} {task.info}')
            time.sleep(0.3)

    def test_infinity_run_extra_urls(self):
        for _ in range(10):
            url = URLForCrawling()
            url.crawling_request_id = ObjectId('63bd34196a6c45902ff46016')
            url.urls.append('https://bsi.de')
            url.save()


if __name__ == '__main__':
    unittest.main()