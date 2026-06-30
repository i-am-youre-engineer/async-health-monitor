import os
import time
import json
import utils
import urllib.request
from datetime import datetime, timedelta
from logger import default_logger


class ProcessorModel:
    def __init__(self, cron_time: str, url: str, timeout_sec: int = 10):
        self.cron_time = cron_time
        self.url = url
        self.timeout_sec = timeout_sec

        # Load logging settings once
        log_config = utils.Config().server['log_file']
        self.log_path = log_config['path']
        self.log_ttl_days = log_config.get('ttl_days', 7)

        # Attributes populated after the request
        self.status_code = None
        self.headers = None
        self.body = None
        self.send_timestamp = None
        self.get_response_timestamp = None
        self.duration = None

    def __call__(self):
        self.__send_request()

    def run(self):
        self.__send_request()

    def process(self):
        self.__send_request()

    def __send_request(self):
        self.send_timestamp = time.time()
        try:
            req = urllib.request.Request(self.url, method='GET')
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                self.status_code = resp.status
                self.headers = dict(resp.getheaders())
                self.body = resp.read()
            self.get_response_timestamp = time.time()
            self.duration = self.get_response_timestamp - self.send_timestamp
            # Success
            self.__save_info()   # error=None
            self.success_send_request(
                send_request=self.send_timestamp,
                get_response=self.get_response_timestamp,
                duration=self.duration
            )
            default_logger.info(f"Processor {self.url} -> {self.status_code} ({self.duration:.2f}s)")
        except Exception as e:
            default_logger.error(f"Processor {self.url} -> {type(e).__name__}")
            self.get_response_timestamp = time.time()
            self.duration = self.get_response_timestamp - self.send_timestamp
            # Log the error
            self.__save_info(error=type(e).__name__)
            self.fail_send_request(
                send_request=self.send_timestamp,
                get_response=self.get_response_timestamp,
                exception=e
            )

    def success_send_request(self, send_request: float, get_response: float, duration: float):
        pass

    def fail_send_request(self, send_request: float, get_response: float, exception: Exception):
        pass

    def __save_info(self, error: str = None):
        record = {
            "ts": datetime.now().isoformat(),
            "url": self.url,
            "status": self.status_code,
            "duration": round(self.duration, 4) if self.duration is not None else 0,
            "cron": self.cron_time,
            "error": error
        }
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        if not os.path.exists(self.log_path):
            return
        cutoff = datetime.now() - timedelta(days=self.log_ttl_days)
        temp_file = self.log_path + ".tmp"
        with open(self.log_path, "r", encoding="utf-8") as src, \
             open(temp_file, "w", encoding="utf-8") as dst:
            for line in src:
                try:
                    rec = json.loads(line.strip())
                    ts = datetime.fromisoformat(rec["ts"])
                    if ts >= cutoff:
                        dst.write(line if line.endswith('\n') else line + '\n')
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        os.replace(temp_file, self.log_path)

    @classmethod
    def test_load(cls):
        default_logger.info(f"Processor {cls.__qualname__} loaded")

class Processor(ProcessorModel):
    pass