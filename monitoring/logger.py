import json
import time
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from loguru import logger
from .config import MonitoringConfig


class StructuredLogger:
    """Logger estruturado para APIs enterprise"""

    def __init__(self):
        self.config = MonitoringConfig()
        self._setup_logger()


    def _setup_logger(self):
        """Configura o sistema de logging estruturado"""

        logger.remove()

        self.config.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            sink=lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
            level=self.config.LOG_LEVEL,
            colorize=True,
        )

        logger.add(
            sink=str(self.config.LOG_FILE_PATH),
            level=self.config.LOG_LEVEL,
            rotation=self.config.LOG_ROTATION,
            retention=self.config.LOG_RETENTION,
            serialize=True,
            enqueue=True,
        )

    def _get_json_format(self, record):
        """Formato JSON estruturado - função que retorna string"""

        log_entry = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        if "extra" in record and record["extra"]:
            log_entry.update(record["extra"])

        return json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ):
        """Log estruturado de requisições HTTP"""

        if status_code >= 500:
            level = "ERROR"
        elif status_code >= 400:
            level = "WARNING"
        elif duration > self.config.SLOW_REQUEST_THRESHOLD:
            level = "WARNING"
        else:
            level = "INFO"

        logger.bind(
            event_type="http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            request_id=request_id,
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
            **kwargs,
        ).log(level, f"{method} {path} - {status_code} - {duration * 1000:.2f}ms")

    def log_database_query(
        self,
        query: str,
        duration: float,
        table: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        """Log estruturado de queries de database"""

        level = "WARNING" if duration > self.config.DB_QUERY_SLOW_THRESHOLD else "DEBUG"

        logger.bind(
            event_type="database_query",
            query=query[:200] + "..." if len(query) > 200 else query,
            duration_ms=round(duration * 1000, 2),
            table=table,
            operation=operation,
            **kwargs,
        ).log(level, f"DB Query - {duration * 1000:.2f}ms")

    def log_business_event(
        self, event_name: str, user_id: Optional[str] = None, **context
    ):
        """Log de eventos de negócio importantes"""

        logger.bind(
            event_type="business_event",
            event_name=event_name,
            user_id=user_id,
            context=context,
        ).info(f"Business Event: {event_name}")

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        request_id: Optional[str] = None,
    ):
        """Log estruturado de erros"""

        logger.bind(
            event_type="error",
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=request_id,
            context=context or {},
        ).error(f"Error: {type(error).__name__}: {str(error)}")


structured_logger = StructuredLogger()
