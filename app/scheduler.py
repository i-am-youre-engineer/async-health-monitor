import time
import utils
import datetime
from logger import default_logger
from utils import cron_match, get_processor_class


class Scheduler:
    def _execute_tasks(self, cron_expr: str):
        config = utils.Config().scheduler
        tasks = config.get(cron_expr, {})
        for url, class_path in tasks.items():
            try:
                proc_class = get_processor_class(class_path)
                # Pass cron_time, url and timeout to the processor
                processor = proc_class(cron_time=cron_expr, url=url, timeout_sec=10)
                # Processor is callable (__call__) — it executes the request automatically
                processor()
                default_logger.info(f"EXEC {class_path} -> {url}")
            except Exception as e:
                default_logger.error(f"EXEC {class_path} -> {url}: {e}")

    def run_forever(self):
        config = utils.Config().scheduler
        default_logger.info("SCHEDULER started")
        while True:
            now = datetime.datetime.now()
            current_minute = now.replace(second=0, microsecond=0)
            for cron_expr in config:
                if cron_match(cron_expr, current_minute):
                    default_logger.debug(f"CRON {cron_expr}")
                    self._execute_tasks(cron_expr)

            # Sleep until the beginning of the next minute
            next_minute = current_minute + datetime.timedelta(minutes=1)
            sleep_seconds = (next_minute - datetime.datetime.now()).total_seconds()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)