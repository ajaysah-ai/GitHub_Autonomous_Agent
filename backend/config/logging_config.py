import json, time
import logging
import traceback
from pathlib import Path
from datetime import datetime

Path("logs").mkdir(exist_ok=True)


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord):

        log = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # extra fields
        for key, value in record.__dict__.items():

            if key not in (
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                log[key] = value

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False, default=str)


def get_logger(name: str):

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(
        f"logs/{name}.jsonl",
        encoding="utf-8",
    )

    handler.setFormatter(JsonFormatter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger


mcp_log = get_logger("github_mcp_server")
requirement_log = get_logger("requirements_graph")
readme_log = get_logger("readme_graph")
action_execute_log = get_logger("action_execute_graph")