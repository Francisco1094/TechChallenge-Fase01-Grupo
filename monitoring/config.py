from typing import Dict, Any
from pathlib import Path
import os

class MonitoringConfig:
    """Configurações centralizadas para monitoramento"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: Path = Path("logs/app.log")
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    METRICS_PATH: str = "/metrics"
    
    SLOW_REQUEST_THRESHOLD: float = 1.0
    ENABLE_REQUEST_BODY_LOGGING: bool = False
    MAX_REQUEST_BODY_SIZE: int = 1024
    
    DB_QUERY_SLOW_THRESHOLD: float = 0.5
    
    @classmethod
    def get_log_config(cls) -> Dict[str, Any]:
        """Retorna configuração do logger"""
        return {
            "level": cls.LOG_LEVEL,
            "format": cls.LOG_FORMAT,
            "file_path": cls.LOG_FILE_PATH,
            "rotation": cls.LOG_ROTATION,
            "retention": cls.LOG_RETENTION
        }