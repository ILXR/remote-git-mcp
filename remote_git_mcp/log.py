import logging
import os
import sys

from rich.text import Text


class StreamLoggerWriter(object):
    def __init__(self, logger, level, parse_ansi: bool = True):
        """
        Args:
            parse_ansi: 是否解析ANSI转义码(比如控制台输出颜色等)
        """
        self._logger = logger
        self._level = level
        self._msg = ""
        self._parse_ansi = parse_ansi

    def _log(self, message):
        if self._parse_ansi:
            text_object = Text.from_ansi(message)
            self._logger.log(self._level, text_object.plain)
        else:
            self._logger.log(self._level, message)

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


def init_log(
    level: int = logging.DEBUG,
    handle_stdout: bool = False,
    handle_stderr: bool = True,
):
    """
    Args:
        handle_stdout (bool, optional): 是否捕获STDOUT到内建logger, 会影响stdio传输协议
        handle_stderr (bool, optional): 是否捕获STDERR到内建logger, 推荐开启
    """
    current_file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(current_file_path, "logs")
    log_file = os.path.join(log_dir, "remote-git-mcp.log")
    print(f"Log will be written to: {log_file}")

    os.makedirs(log_dir, exist_ok=True)
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=5,
        encoding="utf-8",
    )
    handler.suffix = "%Y%m%d"
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
    )

    if handle_stdout:
        stdout_logger = logging.getLogger("STDOUT")
        sys.stdout = StreamLoggerWriter(stdout_logger, logging.INFO)

    if handle_stderr:
        stderr_logger = logging.getLogger("STDERR")
        sys.stderr = StreamLoggerWriter(stderr_logger, logging.WARNING)
