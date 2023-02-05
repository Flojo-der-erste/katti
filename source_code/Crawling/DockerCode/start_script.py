import argparse
import logging
import subprocess

from KattiLogging.LogDocument import DockerLog
from pyvirtualdisplay import Display
from selenium.webdriver import Proxy
from selenium.webdriver.common.proxy import ProxyType
from Crawling.DockerCode.CrawlerExecuter import CrawlerExecuter
from Crawling.DockerCode.DockerKonstanten import GET_WEBDRIVER_EXECUATBLE_PATH
from DataBaseStuff.ConnectDisconnect import establish_db_connection, connect_to_database
from KattiLogging.KattiLogging import setup_logger
from RedisCacheLayer.RedisMongoCache import ManualConnectionSettings
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
#docker run -v ~/shared:/home/drwho_docker/host --ch_id 2 --mongo_uri mongodb://192.168.108.45:27017/ --redis_host 192.168.108.31 --redis_port 6379 --redis_pw test

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ch_id', dest='channel_id', default='Test')
    parser.add_argument('--log_name', dest='logger_name', default='test')
    parser.add_argument('--log_level', dest='logger_level', default=logging.DEBUG)
    parser.add_argument('--mongo_uri', dest='mongo_uri', default="mongodb://katti:test@192.168.15.4:27017/?authMechanism=DEFAULT&authSource=admin")
    parser.add_argument('--redis_host', dest='redis_host')
    parser.add_argument('--redis_port', dest='redis_port')
    parser.add_argument('--redis_pw', dest='redis_pw')
    parser.add_argument('--redis_user', dest='redis_user', default=None)
    parser.add_argument('--task_id', dest='task_id', default='test')
    parser.add_argument('--test', dest='test', default=0)
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    match args.test:
        case '1':
            display = Display(size=(500, 500), visible=False)
            display.start()
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            service = ChromeService(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('chrome'),

                              service_args=[])

            driver = webdriver.Chrome(
                                      options=options,
                                      service=service)
            driver.get('https://bsi.de')
            print(driver.requests)
            display.stop()
            print('1')
        case '2':
            display = Display(size=(500, 500), visible=False)
            display.start()
            options = webdriver.ChromeOptions()
            options.binary_location = '/usr/bin/chromium'
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            service = ChromeService(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('chrome'),
                                    service_args=[])

            driver = webdriver.Chrome(seleniumwire_options={'port': 30005},
                                      options=options,
                                      service=service)
            driver.get('https://bsi.de')
            print(driver.requests)
            print('2')

            display.stop()
        case '3':
            display = Display(size=(1000, 1000), visible=False)
            display.start()
            options = EdgeOptions()
            options.add_argument("--proxy-server=127.0.0.1:30004")
            options.accept_insecure_certs = True
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            service = EdgeService(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('msedge'),

                                  log_path='/home/drwho_docker/selenium.logs', service_args=['--verbose'])

            driver = webdriver.Edge(seleniumwire_options={'port': 30004},
                                    options=options,
                                    service=service)
            driver.get('https://inuit.com')
            print(driver.requests)
            print('edge')
            display.stop()
        case '4':
            display = Display(size=(1000, 1000), visible=False)
            display.start()
            driver = webdriver.Firefox(executable_path=GET_WEBDRIVER_EXECUATBLE_PATH('gecko'))
            driver.get('https://bsi.de')
            print(driver.requests)
            print('4')

            display.stop()
        case _:
            connect_to_database(uri=args.mongo_uri)
            logger = setup_logger(name=args.logger_name, level=args.logger_level, log_class=DockerLog, docker_celery_task_id=args.task_id)
            logger.info('Start crawler')
            logger.info(f'{args.channel_id}')
            establish_db_connection(mongodb_uri=args.mongo_uri)

            try:
                crawler = CrawlerExecuter(logger=logger, channel_id=args.channel_id, redis_con_data=ManualConnectionSettings(host=args.redis_host, port=args.redis_port, user=args.redis_user, password=args.redis_pw))
                crawler.run()
            except KeyboardInterrupt:
                logger.info('Shutdown.')