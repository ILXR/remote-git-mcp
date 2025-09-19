# 日志相关配置
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

# 当前文件路径
current_file_path = os.path.dirname(os.path.abspath(__file__))
# 日志路径
log_path = os.path.join(current_file_path, "logs")
# 每天轮转，旧文件加日期后缀
os.makedirs(log_path, exist_ok=True)
handler = TimedRotatingFileHandler(
    filename=os.path.join(log_path, "server-code-mcp.log"),
    when="midnight",
    backupCount=5,
    encoding="utf-8",
)
handler.suffix = "%Y%m%d"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",  # 显示到秒，不显示微秒
    handlers=[handler],
)


# handle stdout and stderr
class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

    def isatty(self):
        """Return False since this is not a terminal."""
        return False

    def fileno(self):
        """Return a fake file descriptor."""
        return -1


stdout_logger = logging.getLogger("STDOUT")
sys.stdout = StreamToLogger(stdout_logger, logging.INFO)
stderr_logger = logging.getLogger("STDERR")
sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)
