import datetime
import threading
import time
from DataBaseStuff.MongoengineDocuments.KattiServices.CalidogCertStream import CaliDogCertStreamDB, \
    CalidogCerstreamEntry
from KattiServices.BaseKattiSerivce import BaseKattiService
from KattiServices.Certstream.CertStreamClient import listen_for_events,ThreadData


class CalidogCerstream(BaseKattiService):
    db_document: CaliDogCertStreamDB

    @property
    def db_document_cls(self):
        return CaliDogCertStreamDB

    def _next_control_round(self):
        self._certstream_client_data.is_x_509_log_entry = self.db_document.X509LogEntry
        self._certstream_client_data.is_precert_log_entry = self.db_document.PrecertLogEntry
        if self._certstream_client_data.entry_list_len > self.db_document.entries_before_bulk:
            CalidogCerstreamEntry._get_collection().bulk_write(self._certstream_client_data.get_list_and_reset())

    def _shutdown(self):
        self._certstream_client_data.stop_event.set()
        self.logger.info('Wait for shutdown of thread.')
        start = datetime.datetime.utcnow()
        while (datetime.datetime.utcnow() - start).seconds < 10 and self._certstream_client_thread.is_alive():
            time.sleep(0.2)

    def _init(self):
        pass

    def _prepare_service(self):
        self._sleep_time = 10
        self._certstream_client_data = ThreadData(X509LogEntry=self.db_document.X509LogEntry, PrecertLogEntry=self.db_document.PrecertLogEntry)
        self._certstream_client_thread = threading.Thread(target=listen_for_events, args=(self.db_document.certstream_url,
                                                                                          self.logger.getChild('cerstream_client'),
                                                                                          self._certstream_client_data))
        self.logger.info('Start cerstream client.')
        self._certstream_client_thread.start()

