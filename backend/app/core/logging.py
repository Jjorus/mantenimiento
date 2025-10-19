import logging, sys, json
from app.core.config import settings

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"level": record.levelname, "msg": record.getMessage(), "logger": record.name}
        return json.dumps(payload, ensure_ascii=False)

def setup_logging():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(settings.LOG_LEVEL)
