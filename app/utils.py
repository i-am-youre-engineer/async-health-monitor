import os
import re
import json
import importlib
import mimetypes
from logger import default_logger
from datetime import datetime

class TemplateEnv:
    """Simple template engine that replaces [[ KEY ]] and [[ KEY:default ]] patterns
    with values from the configuration UI section or fallback defaults."""

    _PATTERN = re.compile(rb'\[\[([^:\]]+)(?::([^\]]*))?\]\]')

    def __init__(self, template: bytes, extra_vars: dict = None):
        config = Config()
        self._env = config.ui.copy()
        # Inject optional message from environment (e.g., error notifications)
        if message := os.environ.get('message'):
            self._env['message'] = message
        if extra_vars:
            self._env.update(extra_vars)

        self.render_template = self._render(template)

    def _render(self, template: bytes) -> bytes:
        """Replace template placeholders with actual values."""

        def replacer(match):
            key = match.group(1).decode('utf-8', errors='ignore')
            default = match.group(2)
            if default is not None:
                default = default.decode('utf-8', errors='ignore')
            else:
                default = None

            if key in self._env:
                return self._env[key].encode('utf-8')

            elif default is not None:
                return default.encode('utf-8')

            else:
                return match.group(0)

        return self._PATTERN.sub(replacer, template)

class Request:
    """Minimal HTTP request parser (method and path only)."""
    def __init__(self, request_data: bytes):
        request_text = request_data.decode('utf-8', errors='ignore')
        request_line = request_text.split('\r\n')[0]
        parts = request_line.split(' ', 2)
        self.method = parts[0] if len(parts) > 0 else ''
        self.path = parts[1] if len(parts) > 1 else '/'

class Response:
    """Builds an HTTP response, serving static files with optional template processing."""
    def __init__(self, request: Request):
        safe_path = os.path.normpath(request.path.lstrip('/'))
        base_dir = os.path.abspath('./files')
        file_path = os.path.abspath(os.path.join(base_dir, safe_path))

        # Prevent directory traversal
        if not file_path.startswith(base_dir):
            self.status_code = 403
            self.data = self._make_response(403, 'Forbidden')
            return

        if request.method != 'GET':
            self.status_code = 405
            self.data = self._make_response(405, 'Method Not Allowed')
            return

        if not os.path.isfile(file_path):
            self.status_code = 404
            self.data = self._make_response(404, 'Not Found')
            return

        try:
            with open(file_path, 'rb') as f:
                body = f.read()
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            self.status_code = 200
            self.data = self._make_response(200, 'OK', body, mime_type)
        except Exception:
            self.status_code = 500
            self.data = self._make_response(500, 'Internal Server Error')

    def _make_response(self, code, reason, body=b'', content_type='text/plain'):
        """Assemble a complete HTTP response (status line, headers, body)."""
        # Prepare extra template variables
        extra_vars = {}
        # If the file is HTML, include dashboard data
        if content_type.startswith('text/html') or content_type == 'application/xhtml+xml':
            log_config = Config().server['log_file']
            log_path = log_config['path']
            extra_vars['dashboard'] = generate_dashboard_html(log_path)

        template = TemplateEnv(body, extra_vars=extra_vars).render_template

        status_line = f"HTTP/1.1 {code} {reason}\r\n"
        headers = (
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(template)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        return status_line.encode() + headers.encode() + template
    
class Config:
    """Load application configuration from a JSON file."""
    def __init__(self):
        self.config_path = os.environ.get('CONFIG_PATH', './config/config.json')
        self.ui = {}
        self.scheduler = {}

        self.__parse_config_file()

    def __parse_config_file(self):
        config = ''
        with open(self.config_path, 'r') as config_file:
            for row in config_file.readlines():
                config += row

        config_json = json.loads(config)

        self.ui = config_json.get('ui', {})
        self.scheduler = config_json.get('scheduler', {})
        self.server = config_json.get('server', {})
        self.processors = config_json.get('processors', [])
        

def cron_match(cron_expr: str, dt: datetime = None) -> bool:
    """Check if the given datetime matches a cron expression (5 fields)."""
    if dt is None:
        dt = datetime.now()
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False

    minutes, hours, dom, month, dow = parts
    current_minute = dt.minute
    current_hour = dt.hour
    current_dom = dt.day
    current_month = dt.month
    current_dow = dt.isoweekday() % 7  # Sunday = 0, Monday = 1 ... Saturday = 6

    def match_field(field: str, current: int) -> bool:
        if field == '*':
            return True
        for item in field.split(','):
            if '/' in item:
                base, step = item.split('/')
                base = base if base != '*' else None
                step = int(step)
                if base is not None:
                    start = int(base)
                    if current < start:
                        continue
                    if (current - start) % step == 0:
                        return True
                else:
                    if current % step == 0:
                        return True
            else:
                if int(item) == current:
                    return True
        return False

    return (match_field(minutes, current_minute) and
            match_field(hours, current_hour) and
            match_field(dom, current_dom) and
            match_field(month, current_month) and
            match_field(dow, current_dow))

def test_load_processor(processors: list, session=False):
    """Verify that all listed processor classes can be imported and have test_load().
    When session=True, errors are logged instead of raising an exception."""
    if 'message' in os.environ:
        del os.environ['message']
    
    for processor in processors:
        try:
            module_path, class_name = processor.rsplit('.', 1)
            module = importlib.import_module(module_path)
            if not hasattr(module, class_name):
                raise AttributeError(f"Class {class_name} not found in {module_path}")

            proc_class = getattr(module, class_name)
            proc_class.test_load()
            default_logger.info(f"LOAD {processor} -> OK")

        except Exception as e:
            if session:
                default_logger.error(f"LOAD {processor} -> {e}")
                os.environ['message'] = f"Fail loads processor '{processor}': {e}"
            else:
                raise Exception(f"Fail loads processor '{processor}': {e}")


def get_processor_class(class_path: str):
    """Import and return a processor class by its fully qualified name."""
    if 'message' in os.environ:
        del os.environ['message']
    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        if not hasattr(module, class_name):
            raise AttributeError(f"Class {class_name} not found in {module_path}")
        proc_class = getattr(module, class_name)
        default_logger.info(f"LOAD {class_path} -> OK")
        return proc_class
    except Exception as e:
        os.environ['message'] = f"Fail loads processor '{class_path}': {e}"
        default_logger.error(f"LOAD {class_path} -> {e}")
        raise Exception(f"Fail loads processor '{class_path}': {e}")
    
    
def generate_dashboard_html(log_path: str, max_history: int = 20) -> str:
    """
    Reads the JSONL log file and returns an HTML table with the last status
    and a compact history for each monitored URL.
    """
    if not os.path.exists(log_path):
        return '<p>No monitoring data yet.</p>'

    # Read all records
    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line.strip())
                records.append(rec)
            except (json.JSONDecodeError, KeyError):
                continue

    if not records:
        return '<p>No monitoring data yet.</p>'

    # Group by URL
    from collections import defaultdict
    by_url = defaultdict(list)
    for rec in records:
        by_url[rec["url"]].append(rec)

    # Sort each group by timestamp descending
    for url in by_url:
        by_url[url].sort(key=lambda r: r["ts"], reverse=True)

    # Build HTML table rows
    rows = []
    for url, entries in by_url.items():
        last = entries[0]
        status_code = last.get("status")
        if status_code is not None and 200 <= status_code < 300:
            status_text = "UP"
            status_class = "pico-background-jade-500 pico-color-jade-500"
        else:
            status_text = "DOWN"
            status_class = "pico-background-red-500 pico-color-red-500"

        # Форматируем дату последней проверки
        try:
            dt = datetime.fromisoformat(last["ts"])
            last_ts_formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            last_ts_formatted = last["ts"]  # fallback

        last_duration = last.get("duration", 0)

        # История (последние max_history в хронологическом порядке)
        history_entries = entries[:max_history][::-1]
        markers = []
        for rec in history_entries:
            code = rec.get("status")
            # Форматируем время для tooltip
            try:
                t = datetime.fromisoformat(rec["ts"])
                ts_label = t.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_label = rec.get("ts", "?")
            
            if code is not None and 200 <= code < 300:
                color = "#2e7d32"
                status_label = "UP"
            else:
                color = "#c62828"
                status_label = "DOWN"
            
            markers.append(
                f'<span style="display:inline-block;width:12px;height:12px;'
                f'background-color:{color};border-radius:2px;"'
                f' title="{ts_label} — {status_label}"></span>'
            )

        history_html = "".join(markers)

        rows.append(f"""
        <tr>
            <td><code>{url}</code></td>
            <td><mark class="{status_class}">{status_text}</mark></td>
            <td>{last_ts_formatted}</td>
            <td>{last_duration:.3f} s</td>
            <td>{history_html}</td>
        </tr>""")

    table = f"""
    <table class="striped">
        <thead>
            <tr>
                <th>Service URL</th>
                <th>Status</th>
                <th>Last Check</th>
                <th>Response Time</th>
                <th>History ({max_history})</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """
    return table