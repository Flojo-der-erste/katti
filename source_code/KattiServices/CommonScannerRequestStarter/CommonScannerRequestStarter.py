import pickle
from celery.result import AsyncResult
from CeleryApps import KattiApp
from DataBaseStuff.Helpers import execute_bulk_ops
from DataBaseStuff.MongoengineDocuments.KattiServices.CommonScannerRequest import CommonScannerRequest
from DataBaseStuff.MongoengineDocuments.KattiServices.CommonScannerRequestStarter import CommonScannerRequestStarter
from KattiServices.BaseKattiSerivce import BaseKattiService


class CommonScannerRequestStarter(BaseKattiService):
    db_document: CommonScannerRequestStarter

    def _next_control_round(self):
        self._check_task_states()
        if len(self.db_document.running_tasks) >= self.db_document.max_running_tasks:
            return
        help = []
        for next_scanning_request in CommonScannerRequest.get_next_signatures_for_execution(limit=self.db_document.max_running_tasks - len(self.db_document.running_tasks)):
            self.db_document.running_tasks.append(pickle.loads(next_scanning_request.celery_task_signature).apply_async())
            help.append(next_scanning_request.set_lookup_and_cal_next())
        execute_bulk_ops(collection=CommonScannerRequest()._get_collection(), force=True)

    @property
    def db_document_cls(self):
        return CommonScannerRequestStarter

    def _check_task_states(self):
        x = []
        for task in self.db_document.running_tasks:
            if not AsyncResult(task, app=KattiApp).ready():
                x.append(task)
        self.db_document.running_tasks = x

    def _shutdown(self):
        pass

    def _init(self):
        pass

    def _prepare_service(self):
        pass


