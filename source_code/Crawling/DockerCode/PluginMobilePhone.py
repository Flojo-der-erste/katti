import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any


BROWSER_LOGS = []
DOWNLOAD_LOGS = []
BROWSER_LOCK = threading.Lock()
DOWNLOAD_LOCK = threading.Lock()
NEW_DONWLOAD_STARTED = False


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_POST(self):
        global NEW_DONWLOAD_STARTED
        match self.path:
            case '/logs':
                content_length = int(self.headers['Content-Length'])
                if content_length > 0:
                    with BROWSER_LOCK:
                        BROWSER_LOGS.append((json.loads((self.rfile.read(content_length).decode('utf-8')))))
            case '/download':
                content_length = int(self.headers['Content-Length'])
                if content_length > 0:
                    data = json.loads((self.rfile.read(content_length).decode('utf-8')))
                    match data['typ']:
                        case 'new_download':
                            with DOWNLOAD_LOCK:
                                DOWNLOAD_LOGS.append(data)
                                NEW_DONWLOAD_STARTED = True
                        case 'download_state_complete':
                            self._update_download_state(data['id'], 'complete')
                        case 'download_state_interrupted':
                            self._update_download_state(data['id'], 'interrupted')
        self.send_response(200)
        self.end_headers()

    def _update_download_state(self, download_id, new_state):
        with DOWNLOAD_LOCK:
            for download in DOWNLOAD_LOGS:
                if download['id'] == download_id:
                    download['state'] = new_state
                    return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class PluginLogReceiver(threading.Thread):
    def __init__(self):
        super().__init__()
        self._server: ThreadedHTTPServer | None = None

    def run(self):
        print('start')
        self._server = ThreadedHTTPServer(('localhost', 8080), Handler)
        self._server.serve_forever()

    def stop(self):
        if self._server:
            self._server.server_close()

    def all_downloads_finished(self):
        with DOWNLOAD_LOCK:
            for download in DOWNLOAD_LOGS:
                if not download['state'] == 'complete' or not download['state'] == 'interrupted':
                    return False
            return True

    def get_browser_logs(self):
        with BROWSER_LOCK:
            return BROWSER_LOGS

    def get_download_logs(self):
        with DOWNLOAD_LOCK:
            return DOWNLOAD_LOGS

    def reset_new_download(self):
        global NEW_DONWLOAD_STARTED, DOWNLOAD_LOCK
        with DOWNLOAD_LOCK:
            NEW_DONWLOAD_STARTED = False

    def get_new_download_started(self):
        global NEW_DONWLOAD_STARTED, DOWNLOAD_LOCK
        with DOWNLOAD_LOCK:
            return NEW_DONWLOAD_STARTED

    def reset(self):
        global BROWSER_LOGS, DOWNLOAD_LOGS, NEW_DONWLOAD_STARTED, DOWNLOAD_LOCK
        with BROWSER_LOCK:
            BROWSER_LOGS = []
        with DOWNLOAD_LOCK:
            DOWNLOAD_LOGS = []
        NEW_DONWLOAD_STARTED = False


if __name__ == '__main__':
    server = PluginLogReceiver()
    server.start()