# 日志相关配置
import os
import sys
import logging
import fastmcp
from rich.text import Text
from logging.handlers import TimedRotatingFileHandler


# handle stderr
class LoggerWriter(object):
    def __init__(self, logger, level):
        self._logger = logger
        self._level = level
        self._msg = ""

    def _log(self, message):
        text_object = Text.from_ansi(message)
        self._logger.log(self._level, text_object.plain)

    def write(self, message):
        self._msg = self._msg + message
        while "\n" in self._msg:
            pos = self._msg.find("\n")
            self._log(self._msg[:pos])
            self._msg = self._msg[pos + 1 :]

    def flush(self):
        if self._msg != "":
            self._log(self._msg)
            self._msg = ""

    def isatty(self):
        """Return False since this is not a terminal."""
        return False

    def fileno(self):
        """Return a fake file descriptor."""
        return -1


def init_log(enable_stdout: bool = False):
    current_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(current_file_path, "logs")
    log_file_name = os.path.join(log_dir, "remote-git-mcp.log")

    os.makedirs(log_dir, exist_ok=True)
    handler = TimedRotatingFileHandler(
        filename=log_file_name,
        when="midnight",
        backupCount=5,
        encoding="utf-8",
    )
    handler.suffix = "%Y%m%d"
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler] + ([logging.StreamHandler()] if enable_stdout else []),
    )

    # Log the file path after logging is configured
    logging.info(f"log file path: {os.path.abspath(log_file_name)}")

    stderr_logger = logging.getLogger("STDERR")
    sys.stderr = LoggerWriter(stderr_logger, logging.WARNING)
