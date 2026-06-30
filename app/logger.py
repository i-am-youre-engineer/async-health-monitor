import datetime
import os

# ANSI escape codes for console colors
COLOR_RESET = "\033[0m"
COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",    # Red
}

class Logger:
    def __init__(self, name: str = "root", log_file: str = None):
        self.name = name
        self.log_file = log_file
        if self.log_file:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _format(self, level: str, message: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"

    def _log(self, level: str, message: str):
        # Console output with color
        color = COLORS.get(level, "")
        console_msg = f"{color}{self._format(level, message)}{COLOR_RESET}"
        print(console_msg)

        # Write to file without color codes
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(self._format(level, message) + "\n")

    def debug(self, message: str):
        self._log("DEBUG", message)

    def info(self, message: str):
        self._log("INFO", message)

    def warning(self, message: str):
        self._log("WARNING", message)

    def error(self, message: str):
        self._log("ERROR", message)

default_logger = Logger(log_file="./data/server.log")