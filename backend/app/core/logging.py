import json
import logging


class JSONFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        # Redact API Keys if they accidentally get logged
        import re

        message = re.sub(
            r"(api[_-]?key)=([a-zA-Z0-9_\-]+)", r"\1=***", message, flags=re.IGNORECASE
        )
        message = re.sub(
            r"(Authorization: Bearer\s+)([a-zA-Z0-9_\-\.]+)",
            r"\1***",
            message,
            flags=re.IGNORECASE,
        )
        message = re.sub(
            r"(X-API-Key:?\s*)([a-zA-Z0-9_\-]+)", r"\1***", message, flags=re.IGNORECASE
        )

        log_record = {
            "level": record.levelname,
            "name": record.name,
            "message": message,
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            log_record["exc_info"] = (
                "Redacted stacktrace"
                if record.levelname in ["ERROR", "CRITICAL"]
                else self.formatException(record.exc_info)
            )
        return json.dumps(log_record)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # URL của request Fact Check có thể chứa truy vấn trích từ bài đăng.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
