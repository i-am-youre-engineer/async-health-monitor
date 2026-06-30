# Async Health Monitor

A lightweight, zero-dependency async web server and cron-based health-check
monitor written in pure Python. It serves static files with a simple
template engine, periodically pings configured URLs, logs results, and
allows users to extend behaviour through custom processor plugins.

## What problem does it solve?

- You need a **simple dashboard** to show the status of multiple services.
- You want to **periodically check** HTTP endpoints and store response
  metrics (status code, duration, errors).
- You don't want to install heavy frameworks – everything runs on the
  Python standard library (`asyncio`, `urllib`, `json`, etc.).
- You need to **customise alerts** when a health-check fails, without
  touching the core code.
- You prefer configuration over code for endpoints, cron schedules, and
  UI theming.

## Features

- **Async HTTP server** – serves static files (HTML, CSS, JS) from the
  `./files` directory.
- **Template engine** – `[[KEY]]` and `[[KEY:default]]` placeholders
  are replaced with values from the `ui` section of the config file.
- **Built-in scheduler** – runs as a separate daemon process, evaluates
  cron expressions, and triggers HTTP requests.
- **Pluggable processors** – inherit from `ProcessorModel`, override
  `success_send_request` and `fail_send_request`, and drop your class
  into the `processors/` folder.
- **Structured logging** – coloured console output, plain-text file logs
  for the server, and JSON Lines logs for processor results with
  automatic cleanup (configurable TTL).
- **Security** – directory traversal protection, only GET requests are
  served, unknown paths return 404.
- **Zero dependencies** – everything comes from the Python standard
  library.

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd async-health-monitor/app
   ```

2. **Prepare the configuration**

    The default config file is `./config/config.json`. You can override
    its location with the `CONFIG_PATH` environment variable.

3. **Create static files**

    Place your HTML, CSS, JS files inside the `./files` directory.
    For example:

    ```text
    files/
    ├── index.html
    ├── dashboard.html
    ├── css/
    │   └── pico.min.css
    └── js/
        └── script.js
    ```

4. **Run the server**

    ```bash
    python server.py
    ```
    The server starts on `http://0.0.0.0:8080` (configurable). The
    scheduler daemon will also begin executing cron tasks immediately.

5. **View the dashboard**

Open `http://localhost:8080/dashboard.html` (or your custom page).

# Configuration Reference

All settings live in `config/config.json.`

## `server`
```json
"server": {
    "host": "0.0.0.0",
    "port": 8080,
    "run_with_error": true,
    "server_log": "./data/server.log",
    "log_file": {
        "path": "./data/logs.jsonl",
        "ttl_days": 7
    }
}
```

|Key|Description|
|-|-|
|`host`|IP address to bind the HTTP server.|
|`port`|TCP port to listen on.|
|`run_with_error`|If `true`, processor loading errors are logged but the server still starts. If `false`, the server aborts on the first error.|
|`server_log`|Path to the plain-text log file for HTTP requests and server events.|
|`log_file.path	`|Path to the JSON Lines file where processor results are stored.|
|`log_file.ttl_days	`|Number of days to keep processor logs; older entries are removed automatically.|

## `server`

```json
"ui": {
    "theme": "dark",
    "colors": "grey",
    "title": "System health monitoring",
    "description": "This is testing description."
}
```
These key-value pairs are exposed to the template engine. In your HTML
files you can write `[[theme:]]` or `[[colors:pumpkin]]` to inject
the configured values (or fall back to the default after the colon).

## `processors`
```json
"processors": [
    "processor.Processor",
    "processors.example.ExampleProcessor"
]
```
A list of fully qualified class paths. On startup the server verifies
that each class can be imported and has a `test_load()` method. These
processors are not executed at startup; they are only used when
referenced in the `scheduler` section.

Each key is a **cron expression** (minute, hour, day of month, month,
day of week). The value is a mapping of **URL → processor class**.
When the cron expression matches the current minute, the scheduler
creates an instance of the specified processor and calls it with the
given URL.

Supported cron features:
* Wildcard `*`
* Exact numbers `5`
* Steps `*/10` (every 10 minutes)
* Lists `1,3,5`

## Writing a Custom Processor
1. Create a new file inside `processors/` (or any importable location).

2. Import `ProcessorModel` and inherit from it.

3. Override `success_send_request` and/or `fail_send_request`.

4. Optionally override `test_load` to print a custom message.

Example:
```python
from processor import ProcessorModel

class MyAlertProcessor(ProcessorModel):
    def fail_send_request(self, send_request, get_response, exception):
        super().fail_send_request(send_request, get_response, exception)
        # Your custom logic: send a Telegram message, write to a DB, etc.
        print(f"ALERT: {self.url} is down! ({exception})")
```

5. Add `"processors.my_module.MyAlertProcessor"` to the `processors`
list in `config.json`.

6. Use it in the `scheduler` section for the URLs you want to monitor.

# Project Structure
```text
.
├── server.py              # Async HTTP server entry point
├── scheduler.py           # Cron scheduler (runs in a separate process)
├── utils.py               # Config, Request/Response, template engine, helpers
├── logger.py              # Coloured console + file logger
├── processor.py           # Base processor model
├── processors/
│   └── example.py         # Example custom processor
├── files/                 # Static files served by the web server
├── data/                  # Logs and processor results (git-ignored)
├── config/
│   └── config.json        # Main configuration file
└── README.md
```

# Logging

* **Console**: colour-coded output for quick debugging.
    * `DEBUG` – cron triggers.
    * `INFO` – successful HTTP responses, processor executions, server
start/stop.
    * `WARNING` – client errors (4xx).
    * `ERROR` – server errors (5xx), processor failures.
* **File**: plain text log at the path specified by `server_log`.
* **Processor results**: JSON Lines file at `log_file.path`, containing
for each request:

    ```json
    {
    "ts": "2026-06-30T16:02:00",
    "url": "http://0.0.0.0:8080/dashboard.html",
    "status": 200,
    "duration": 0.023,
    "cron": "* * * * *",
    "error": null
    }
    ```

    Old records are automatically removed after `log_file.ttl_days`.

# Why no external dependencies?

The project is intentionally kept dependency-free so that it can run on
any system with Python 3.10+ without installing additional packages.
This makes it ideal for embedded environments, containers, or situations
where you want full control over the stack.

Happy monitoring!

## License

This project is licensed under the terms of the MIT License.  
See the [LICENSE](LICENSE) file for details.