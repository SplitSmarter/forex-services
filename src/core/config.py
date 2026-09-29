import os
import sys
import logging
from datetime import datetime, timezone
from contextvars import ContextVar
from dotenv import load_dotenv

ENV = os.getenv("ENV", "dev")

# ==== Environment Config ====

if ENV in ("prod", "dev"):
    load_dotenv(".env")
else:
    raise Exception("Must provide a suitable Environment")

APP_NAME = os.getenv("APP_NAME", "forex-service")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Database Configuration
FOREX_DATABASE_URL = os.getenv(
    "FOREX_DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/forex_db",
)

# External API Configuration
currency_layer_api_url = "http://api.currencylayer.com/live"
exchange_rate_api_url = "https://v6.exchangerate-api.com/v6"
CURRENCYLAYER_ACCESS_KEY = os.getenv("CURRENCYLAYER_ACCESS_KEY")
EXCHANGERATE_ACCESS_KEY = os.getenv("EXCHANGERATE_ACCESS_KEY")

# Rate Refresh Configuration
RATE_REFRESH_INTERVAL_HOURS = int(os.getenv("RATE_REFRESH_INTERVAL_HOURS", "1"))
ENABLE_DB_SCHEMA_INIT = os.getenv("ENABLE_DB_SCHEMA_INIT", "true").lower() in ("true", "1", "yes", "on")

# Logging Configuration
TRACE_ID_KEY = "trace_id"
TRACE_ID_HEADER_NAME = "X-Trace-Id"
ctx_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")

class UTCFormatter(logging.Formatter):
    """Custom UTC formatter for consistent timestamps."""
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(trace_id)s] - %(name)s - %(module)s - %(funcName)s - %(message)s"
formatter = UTCFormatter(LOG_FORMAT)

# Stream handler → stdout (container/docker friendly)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# File handler
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/forex-service.log")
file_handler.setFormatter(formatter)

# Application logger
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO if ENV == "prod" else logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.propagate = False

class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        trace_id = ctx_trace_id.get()
        extra = kwargs.get("extra", {})
        kwargs["extra"] = {TRACE_ID_KEY: trace_id, **self.extra, **extra}
        return msg, kwargs

def get_request_logger(**context) -> logging.LoggerAdapter:
    return ContextLoggerAdapter(logger, context)

def get_logger(**context) -> logging.LoggerAdapter:
    return get_request_logger(**context)
