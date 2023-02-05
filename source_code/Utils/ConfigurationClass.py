import os.path
from dataclasses import dataclass, field
import yaml
from pydantic import RedisDsn, AmqpDsn


DATBASE_CONFIG_OBJC = None
CONFIG_FILES = os.path.expanduser('~/katti/config')
@dataclass
class Redis:
    user: str
    port: int
    password: str
    host: str


@dataclass
class DatabaseConfigs:
    mongodb_configs: dict[str, str]  # MongoDsn doesn't work
    redis: Redis

    @classmethod
    def get_config(cls):
        global DATBASE_CONFIG_OBJC
        if not DATBASE_CONFIG_OBJC:
            with open(os.path.join(CONFIG_FILES, 'database_configs.yml'), 'r') as raw_file:
                config = yaml.safe_load(raw_file)
                DATBASE_CONFIG_OBJC = cls(redis=Redis(**config['redis']), mongodb_configs=config['mongodb'])
        return DATBASE_CONFIG_OBJC

    @property
    def redis_url(self):
        return f'redis://{self.redis.user}:{self.redis.password}@{self.redis.host}:{self.redis.port}'

    def get_mongodb_uri_for_user(self, user='katti'):
        return self.mongodb_configs[user]


@dataclass
class FastAPIConfig:
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        match len(self.meta.keys()):
            case 0:
                self.meta.update({
                    'title': "Katti's amazing API",
                    'description': "Katti helps you do awesome stuff. 🚀",
                    'contact': {
                        'name': "Dr. Who",
                        'email': "drwho@gallifrey.com"
                    }})

    @classmethod
    def get_config(cls):
        with open(os.path.join(CONFIG_FILES, 'fastapi.yml'), 'r') as raw_file:
            config_file = yaml.safe_load(raw_file)
            return cls(**config_file)


@dataclass
class CeleryConfig:
    broker: AmqpDsn
    task_serializer: str
    result_serializer: str
    accept_content: list[str]
    redis_db_nr: int

    @classmethod
    def get_config(cls):
        with open(os.path.join(CONFIG_FILES, 'celery.yml'), 'r') as raw_file:
            config_file = yaml.safe_load(raw_file)
            return cls(**config_file)

@dataclass
class Docker:
    docker_host: str
    crawler_docker_container_name: str
    extra_args: dict

    @classmethod
    def get_config(cls):
        with open(os.path.join(CONFIG_FILES, 'docker.yml'), 'r') as raw_file:
            config_file = yaml.safe_load(raw_file)
            return cls(**config_file)

