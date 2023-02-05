from abc import ABC, abstractmethod
from DataBaseStuff.MongoengineDocuments.Crawling_BrowserConfiguration.CrawlingConfiguration import CrawlingConfig
from Crawling.DockerCommunicatorServer import IFrameFun, FakeUserInteraction, DockerCommunicatorServer


class BaseWorkFlowFunction(ABC):

    @abstractmethod
    def workflow(self, communicator: DockerCommunicatorServer, browser_config, crawling_config: CrawlingConfig):
        pass


class Ad_Workflow(BaseWorkFlowFunction):
    def workflow(self, communicator: DockerCommunicatorServer, browser_config,
                 crawling_config: CrawlingConfig):
        communicator.send_command(cmd=IFrameFun(depth=1), wait_time_for_execution=crawling_config.docker_wait_ad_fun)


class Anti_Bot(BaseWorkFlowFunction):
    def workflow(self, communicator: DockerCommunicatorServer, browser_config,
                 crawling_config: CrawlingConfig):
        communicator.send_command(cmd=FakeUserInteraction(),
                                  wait_time_for_execution=crawling_config.docker_wait_for_user_actions)


