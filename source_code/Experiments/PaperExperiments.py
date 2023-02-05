import datetime
import unittest
import requests
from FastAPI.CrawlingRouter.CrawlingRequestFastAPI import MultiBrowserURLS

HOST = '192.168.177.86'

class Experiments(unittest.TestCase):

    def setUp(self):
        self.urls = []
        with open('top-1m.csv', 'r') as file:
            lines = file.readlines()
            for i in range(1000):
                domain = lines[i].split(',')[-1]
                domain = domain.rstrip()
                self.urls.append(f'https://{domain}')


    def start_experiment(self, api_request_data: MultiBrowserURLS ):
        start = datetime.datetime.utcnow()
        response = requests.post(f'http://{HOST}:8000/api/crawling/execute_crawling_request/fast/multi_browser_urls', data=api_request_data.json())
        print(response.content)

    def test_experiment(self):
        self.start_experiment(MultiBrowserURLS(browser=['Chrome', 'Edge', 'Firefox', 'Chromium'], tag_name='Test api',
                                               analyses=['google'], urls=self.urls))

if __name__ == '__main__':
    unittest.main()




