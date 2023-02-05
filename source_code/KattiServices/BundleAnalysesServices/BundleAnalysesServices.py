import datetime
from CeleryApps.CrawlingTasks import bundle_analysis
from DataBaseStuff.MongoengineDocuments.Crawling.PreCrawlingAnalyseSettings import BundleAnalyseCandidate
from DataBaseStuff.MongoengineDocuments.KattiServices.BundleServiceAnalyse import BundleAnalyseTaskStarter
from KattiServices.BaseKattiSerivce import BaseKattiService


class BundleAnalysesService(BaseKattiService):
    db_document: BundleAnalyseTaskStarter

    @property
    def db_document_cls(self):
        return BundleAnalyseTaskStarter

    def _next_control_round(self):
        self.db_document.running_tasks = self._check_task()
        if len(self.db_document.running_tasks) >= self.db_document.max_running_tasks:
            self.sleep_time = 60
            return
        arg = [{'$match': {'next_execution': {'$lte': datetime.datetime.utcnow() + datetime.timedelta(days=1)}}},
               {'$sort': {'priority': -1, 'next_execution': 1}},
               {'$limit': self.db_document.max_running_tasks - len(self.db_document.running_tasks)},
               {'$project': {'_id': 1}}]
        x = []
        for bundle_candidate in BundleAnalyseCandidate.objects().aggregate(arg):
            self.db_document.running_tasks.append(bundle_analysis.apply_async(args=(bundle_candidate['_id'])))
            x.append(bundle_candidate['_id'])
        BundleAnalyseCandidate.objects(id__in=x).delete()

    def _check_task(self):
        x = []
        for task_id in self.db_document.running_tasks:
            if not bundle_analysis.AsyncResult(task_id).ready():
                x.append(task_id)
        return x

    def _shutdown(self):
        pass

    def _init(self):
        pass

    def _prepare_service(self):
        pass