from mongoengine import IntField, FloatField, ObjectIdField
from DataBaseStuff.MongoengineDocuments.BaseDocuments import BaseConfig


class CrawlingConfig(BaseConfig):
    dns_pre_check_scanner_id = ObjectIdField(required=True)
    
    wait_time_for_docker_ready = IntField(min_value=0, default=60*2)

    docker_max_docker_restarts = IntField(min_value=1, default=2)

    docker_common_wait_time_for_answer = IntField(min_value=1, default=10)
    docker_wait_time_reset = IntField(min_value=1, default=5)
    docker_wait_window_stats_execution = IntField(min_value=0, default=60)
    docker_wait_ping_pong = IntField(min_value=1, default=10)
    docker_wait_ad_fun = IntField(min_value=0, default=60 * 10)
    docker_wait_for_save_data = IntField(min_value=5, default=60 * 3)
    docker_wait_for_new_webdriver = IntField(min_value=1, default=30)
    docker_wait_for_user_actions = IntField(default=30, min_value=1)

    iframe_wait_before_start = IntField(min_value=0, default=1)
    iframe_click_on_add_tries = IntField(min_value=1, default=10)
    iframe_wait_for_click_reaction = IntField(min_value=1, default=10)
    iframe_sum_wait_for_read_ad_tag = IntField(min_value=1, default=10)
    iframe_min_windows_count_before_production = IntField(min_value=1, default=8)
    iframe_max_reloads_url_changed = IntField(default=3, min_value=0)
    iframe_wait_for_frame_ready = IntField(default=0, min_value=0)
    iframe_min_height = IntField(min_value=1, default=20)
    iframe_min_width = IntField(min_value=1, default=20)
    iframe_max_wait_time_for_all_frames = IntField(min_value=0, default=10)
    iframe_max_visits = IntField(min_value=1, default=2)
    javascript_screenshot_sticht_break = FloatField(min_value=0.0, default=0.1)

    @staticmethod
    def get_config_main_name() -> str:
        return 'crawling_configuration'
