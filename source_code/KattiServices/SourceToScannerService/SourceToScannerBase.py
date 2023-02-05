from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import MetaData
from KattiServices.SourceToScannerService.ScannerExecutionRequestBuilder import ScannerExecutionRequestBuilder
from RedisCacheLayer.RedisMongoCache import RedisMongoCache
from KattiServices.BaseKattiSerivce import BaseKattiService
from Scanner.BaseScanner import OOI


class SourceToScannerBase(BaseKattiService):
    def _execute_next_round(self):
        raise NotImplementedError

    def _end_of_round(self):
        raise NotImplementedError

    def _next_control_round(self):
        self._scanner_requests_insert = []
        self._execute_next_round()
        self._end_of_round()
        for builders in self._scanner_request_builders:
            builders.save_final_crawling_request()

    def _add_to_builders(self, ooi, meta_data=None):
        if meta_data is None:
            meta_data = {}
        meta_data = MetaData(tag=self.db_document.meta_data.tag, **meta_data)
        for scanner_request_builder in self._scanner_request_builders:
            scanner_request_builder.add_new_ooi(OOI(raw_ooi=ooi,
                                                    meta_data_obj=meta_data))

    def _shutdown(self):
        pass

    def _init(self):
        pass

    def _prepare_service(self):
        self._redis_cache = RedisMongoCache()
        self._scanner_request_builders: list[ScannerExecutionRequestBuilder] = [ScannerExecutionRequestBuilder(ownership=self.db_document.ownership, meta_data=self.db_document.meta_data).set_execution_information(execution_info) for execution_info in self.db_document.execution_information]


