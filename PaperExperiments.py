import datetime
import unittest
import uuid
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import KattiUser
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

        self.ownership = Ownership(owner=KattiUser.objects.get(first_name='Dr. Who?'))

    def start_experiment(self, browser_group, tag):
        crawling_config = CrawlingConfig.objects.get(name='default_crawling')
        meta = MetaData(tag=tag.id)
        crawling_r = CrawlingRequest(id=ObjectId(), ownership=self.ownership, crawling_config=crawling_config,
                                     statefull_crawling=False, operation_group_modi='not_waiting',
                                     dns_check_valid_time=0, katti_meta_data=meta)
        crawling_r.analyses_settings = self.after_anal
        crawling_r.infinity_run = False
        crawling_r.crawling_groups.append(browser_group)
        crawling_r.save()
        with open('top-1m.csv', 'r') as file:
            lines = file.readlines()
            for i in range(1):
                url = URLForCrawling()
                url.max_lookups = 1
                url.crawling_request_id = crawling_r
                domain = lines[i].split(',')[-1]
                domain = domain.rstrip()
                url.urls.append(f'https://{domain}')
                url.save()

        task = crawling_request_celery.apply_async(args=(crawling_r.id,))
        print(f'Crawling request {task.id}')

    def test_experiment_only_chrome_1_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))

        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 1, chrome, 1  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_only_chrome_2_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))

        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 2, chrome, 2  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_only_chrome_3_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))

        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 3, chrome, 3  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_only_chrome_edge_1_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 4, chrome:edge, 1  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_only_chrome_edge_2_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 5, chrome:edge, 2  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_only_chrome_edge_3_vm(self):
        browser_config = BrowserConfig.save_to_db(
            config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config.id)
        tag = Tag(name='Experiment 6, chrome:edge, 3  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_chrome_edge_firefox_1_vm(self):
        browser_config = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_config_3 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=FirefoxOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config_3.id)
        tag = Tag(name='Experiment 7, chrome:edge:firefox, 1  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_chrome_edge_firefox_2_vm(self):
        browser_config = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_config_3 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=FirefoxOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config_3.id)
        tag = Tag(name='Experiment 8, chrome:edge:firefox, 2  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)

    def test_experiment_chrome_edge_firefox_3_vm(self):
        browser_config = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=ChromeOptions()))
        browser_config_2 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=EdgeOptions()))
        browser_config_3 = BrowserConfig.save_to_db(config=BrowserConfig.Config(browser_options=FirefoxOptions()))
        browser_group = BrowserGroup()
        browser_group.browser_configs.append(browser_config.id)
        browser_group.browser_configs.append(browser_config_2.id)
        browser_group.browser_configs.append(browser_config_3.id)
        tag = Tag(name='Experiment 9, chrome:edge:firefox, 3  VM', create=datetime.datetime.utcnow(), owner=self.ownership)
        tag.save()
        self.start_experiment(browser_group, tag)





if __name__ == '__main__':
    unittest.main()




