import io
import sys
import traceback
from tarfile import TarFile
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from bson import ObjectId
from DataBaseStuff.MongoengineDocuments.Crawling.Bundle import Bundle, KattiSurveillanceLogs, ExtensionInstallationLog, \
    HandleAlarmLog, NewWindowLog, NewTabLog, BeforeNavigateLog, SubTiming
from DataBaseStuff.MongoengineDocuments.Crawling.DatabaseHTTPRequest import REQUEST_LOGS, START_RE_LOGS, REDIRECT_LOGS, \
    DatabaseHTTPRequest
from DataBaseStuff.MongoengineDocuments.Crawling.WindowTab import WindowTab
from seleniumwire.request import Request as SwRequest
from DataBaseStuff.GridFsStuff import gridfs_insert_data


class DataToDB:
    def __init__(self, logger):
        self._logger = logger
        self._request_ids = None
        self._redis_cache: RedisMongoCache = RedisMongoCache()

    def saving_it(self,
                  bundle_id: ObjectId,
                  sub_timings: list[SubTiming],
                  seleniumwire_requests: list[SwRequest],
                  browser_logs: list = [],
                  window_stats: list[WindowTab] = [],
                  profile_path='',
                  extra_data={},
                  save_profile_redis=False):
        self._bundle_id = bundle_id
        new_bundle = Bundle(**extra_data)
        try:
            for window in window_stats:
                window.save_it()
            if len(window_stats) > 0:
                new_bundle.window_tab_pop_attributes = window_stats
            new_bundle.window_pop_tab_counter = len(window_stats)
            try:
                new_bundle.katti_surveillance_logs = self._produce_extension_logs(browser_logs)
            except Exception:
                self._logger.exception(traceback.format_exception(*sys.exc_info()))
            new_bundle.requests = self._save_requests(selenium_wire_requests=seleniumwire_requests)
            new_bundle.requests_count = len(new_bundle.requests)
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
        new_bundle.browser_profile = self.save_browser_profile(path=profile_path, profile_to_redis=save_profile_redis)
        bundle_mongo = new_bundle.to_mongo()
        bundle_mongo.update({'crawling_meta_data.crawling_timings.sub_timings': [x.to_mongo() for x in sub_timings]})
        Bundle.objects(id=self._bundle_id).update_one(__raw__={'$set': bundle_mongo})

    def _produce_extension_logs(self, extension_logs):
        katti_sur_logs = KattiSurveillanceLogs()
        for log in extension_logs:
            match log['typ']:
                case 'new_addon':
                    katti_sur_logs.extension_install_logs.append(ExtensionInstallationLog.build(log))
                case 'new_alarm':
                    katti_sur_logs.alarm_logs.append(HandleAlarmLog.build(log))
                case 'new_window':
                    katti_sur_logs.new_window_logs.append(NewWindowLog.build(log))
                case 'new_tab':
                    katti_sur_logs.new_tab_logs.append(NewTabLog.build(log))
                case 'before_navigate':
                    if not (log['nav_url'] == 'about:blank' or log['nav_url'] == 'data:,') or log[
                        'nav_url'] == 'chrome://new-tab-page/':
                        katti_sur_logs.navigation_logs.append(BeforeNavigateLog.build(log))
                case 'before_request':
                    REQUEST_LOGS.update({log['request_id']: log})
                case 'start_response':
                    START_RE_LOGS.update({log['request_id']: log})
                case 'before_redirect':
                    if log['request_id'] in REDIRECT_LOGS:
                        REDIRECT_LOGS[log['request_id']].append(log)
                    else:
                        REDIRECT_LOGS.update({log['request_id']: [log]})
                case _:
                    katti_sur_logs.unknown_logs.append(log)
        return katti_sur_logs

    def _save_requests(self, selenium_wire_requests: list[SwRequest]):
        request_ids = []
        for request in selenium_wire_requests:
            new_request = DatabaseHTTPRequest.build(raw_request=request, bundle_id=self._bundle_id)
            request_ids.append(new_request.id)
        return request_ids

    def save_browser_profile(self, path, profile_to_redis) -> None:
        if path == '':
            return
        file_like_obj = io.BytesIO()
        tar_file = TarFile(fileobj=file_like_obj, mode='w')
        try:
            tar_file.add(path, arcname='profile')
            value = file_like_obj.getvalue()
            object_id = gridfs_insert_data(data=value, db_name='Katti', meta_data={'type': 'browser_profile', 'bundle': str(self._bundle_id)})
            if profile_to_redis:
                try:
                    self._redis_cache.insert_value_pair(key=str(object_id), value=value)
                except Exception:
                    self._logger.exception(traceback.format_exception(*sys.exc_info()))
        except Exception:
            self._logger.exception(traceback.format_exception(*sys.exc_info()))
            object_id = None
        finally:
            tar_file.close()
            file_like_obj.close()
            return object_id
