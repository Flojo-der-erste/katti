import datetime
import pickle
import time
import typing
import uuid
from dataclasses import dataclass, field

from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import SubTiming

from Crawling.Exceptions import NoDockerAnswer, NoCommandException
from bson import ObjectId


@dataclass
class DockerCMD:
    command_id: uuid.UUID | None = None

    @property
    def cmd_name(self) -> str:
        raise NotImplementedError


@dataclass
class FakeUserInteraction(DockerCMD):
    @property
    def cmd_name(self) -> str:
        return 'fake_user_interaction'


@dataclass
class SaveDataToDBCMD(DockerCMD):

    @property
    def cmd_name(self) -> str:
        return 'save_data_to_db'

@dataclass
class SaveBrowserProfileToDB(DockerCMD):
    save_backup_profile_to_redis: bool = True
    @property
    def cmd_name(self) -> str:
        return 'save_browser_profile_to_db'


@dataclass
class CrawlingCMD(DockerCMD):
    crawling_url: str | None = None
    bundle_id: ObjectId | None = None

    @property
    def cmd_name(self) -> str:
        return 'crawling_url'


@dataclass
class WindowStatsCMD(DockerCMD):
    action_id: str = ''

    @property
    def cmd_name(self) -> str:
        return 'window_stats'


@dataclass
class IFrameFun(DockerCMD):
    depth: int = 1
    click_ads: bool = True

    @property
    def cmd_name(self) -> str:
        return 'iframe_fun'


@dataclass
class Reset(DockerCMD):

    @property
    def cmd_name(self) -> str:
        return 'reset'


@dataclass
class StartWebdriverCMD(DockerCMD):
    display_colour_depth: int = 24

    browser_config_id: ObjectId | None = None

    backup_profile_id: ObjectId | None = None
    ignore_profile_db_error: bool = False

    ignore_extension_download_error: bool = False

    common_crawling_config_id: ObjectId | None = None

    def __post_init__(self):
        if not self.browser_config_id or not self.common_crawling_config_id:
            raise Exception('Browser and Common config are needed.')

    @property
    def cmd_name(self) -> str:
        return 'start_webdriver'




@dataclass
class DownloadFinishedCMD(DockerCMD):

    @property
    def cmd_name(self) -> str:
        return 'downloads_finished'


@dataclass
class PingCMD(DockerCMD):

    @property
    def cmd_name(self) -> str:
        return 'ping'


@dataclass
class DockerAnswer:
    error_code: int = -1
    command_id: uuid.UUID| None = None

@dataclass
class WebdriverStartAnswer(DockerAnswer):
    timing: SubTiming | None = None

@dataclass
class DockerAnswerCrawling(DockerAnswer):
    pass

@dataclass
class DockerAnswerDownloads(DockerAnswer):
    all_finished: bool = False

@dataclass
class PongAnswer(DockerAnswer):
    answer: str = 'Pong baby'


next_cmd = lambda channel_id: f'{channel_id}_cmd'
response_cmd = lambda channel_id: f'{channel_id}_resp'


class DockerCommunicatorServer:
    def __init__(self, channel_id):
        from RedisCacheLayer.RedisMongoCache import set_up_connection
        self.channel_id = channel_id
        self.redis_conn = set_up_connection()
        self.last_command_id = None

    def send_command(self, cmd: typing.Union[DockerCMD], wait_time_for_execution) -> DockerAnswer:
        self._send_command_to_docker(cmd)
        start_time = datetime.datetime.utcnow()
        while (datetime.datetime.utcnow() - start_time).seconds <= wait_time_for_execution:
            answer = self.get_response()
            if answer:
                return answer
            time.sleep(0.1)
        raise NoDockerAnswer(f'CMD: {cmd}')

    def _send_command_to_docker(self, cmd: typing.Union[DockerCMD]):
        self.last_command_id = uuid.uuid4()
        cmd.command_id = self.last_command_id
        self.redis_conn.set(next_cmd(self.channel_id), value=pickle.dumps(cmd), ex=3600)

    def get_response(self):
        answer = self.redis_conn.get(response_cmd(self.channel_id))
        if answer:
            response = pickle.loads(answer)
            if response.command_id == self.last_command_id:
                return response
        return None

    def reset(self, new_channel_id):
        self.channel_id = new_channel_id
        self.last_command_id, self.next_command_id = None, None

    def reset_channel(self):  # Testing. in the wild not necessary
        self.redis_conn.delete(next_cmd(self.channel_id))
        self.redis_conn.delete(response_cmd(self.channel_id))
    def play_ping_pong(self, wait_time_for_execution):
        self.reset_channel()
        self.send_command(PingCMD(), wait_time_for_execution)


class DockerCommunicatorClient:
    def __init__(self, channel_id, redis_con):
        self.channel_id = channel_id
        self.redis_conn = redis_con
        self._last_command_id = None

    def get_next_command(self):
        return self._produce_cmd(self.redis_conn.get(next_cmd(self.channel_id)))

    def send_response(self, response: DockerAnswer):
        response.command_id = self._last_command_id
        self.redis_conn.set(response_cmd(self.channel_id), value=pickle.dumps(response))

    def _produce_cmd(self, cmd: bytes):
        if not cmd:
            raise NoCommandException()
        cmd = pickle.loads(cmd)
        if not self._last_command_id and isinstance(cmd, PingCMD):
            self._last_command_id = cmd.command_id
            return cmd
        if cmd.command_id == self._last_command_id or not self._last_command_id:
                raise NoCommandException
        self._last_command_id = cmd.command_id
        return cmd
