import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from collections import defaultdict, Counter
from .metrics import metrics
from .config import MonitoringConfig

class MetricsExporter:
    """Exportador de métricas para consumo externo - DADOS REAIS"""
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        
    def _read_structured_logs(self, since: Optional[datetime] = None) -> List[Dict]:
        """Lê logs estruturados reais do arquivo JSON"""
        logs = []
        log_file = Path(self.config.LOG_FILE_PATH)
        
        if not log_file.exists():
            return logs
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                            timestamp_raw = log_entry.get('record', {}).get('time', {}).get('timestamp')
                            if timestamp_raw:
                                log_timestamp = datetime.fromtimestamp(timestamp_raw)
                            
                                if since and log_timestamp < since:
                                    continue
                                    
                                log_entry['parsed_timestamp'] = log_timestamp
                                logs.append(log_entry)
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            print(f"Erro ao ler logs: {e}")
            
        return logs
    
    def _extract_prometheus_metrics(self) -> Dict[str, Any]:
        """Extrai métricas reais do Prometheus"""
        try:
            raw_metrics = metrics.get_metrics()
            parsed_metrics = {}
            
            for line in raw_metrics.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                    
                if '{' in line:
                    metric_name = line.split('{')[0]
                    value_part = line.split('}')[1].strip()
                    value = float(value_part) if value_part else 0.0
                    
                    if metric_name not in parsed_metrics:
                        parsed_metrics[metric_name] = []
                    parsed_metrics[metric_name].append(value)
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        metric_name, value = parts[0], float(parts[1])
                        parsed_metrics[metric_name] = value
                        
            return parsed_metrics
            
        except Exception as e:
            print(f"Erro ao extrair métricas Prometheus: {e}")
            return {}
    
    def export_current_metrics(self) -> Dict[str, Any]:
        """Exporta métricas atuais - DADOS REAIS"""
        logs = self._read_structured_logs(since=datetime.now() - timedelta(hours=1))
        # print("##",logs)
        prometheus_metrics = self._extract_prometheus_metrics()
        # Calcular métricas reais dos logs
        http_requests = [log for log in logs 
                        if log.get('record', {}).get('extra', {}).get('event_type') == 'http_request']
        
        business_events = [log for log in logs 
                          if log.get('record', {}).get('extra', {}).get('event_type') == 'business_event']
        
        error_events = [log for log in logs 
                       if log.get('record', {}).get('extra', {}).get('event_type') == 'error']
        
        # print("@@",http_requests)
        return {
            "total_requests": len(http_requests),
            "success_rate": self._calculate_real_success_rate(http_requests),
            "avg_response_time": self._calculate_real_avg_response_time(http_requests),
            "active_users": self._count_real_active_users(logs),
            "error_rate_5xx": self._calculate_real_error_rate(http_requests, "5xx"),
            "error_rate_4xx": self._calculate_real_error_rate(http_requests, "4xx"),
            "failed_logins_rate": self._calculate_real_failed_logins_rate(business_events),
            "current_timestamp": datetime.utcnow().isoformat(),
            "http_requests": logs,
            "data_source": "real_logs_and_prometheus"
        }
    
    def export_historical_data(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """Exporta dados históricos - DADOS REAIS"""
        since = datetime.utcnow() - timedelta(hours=hours)
        logs = self._read_structured_logs(since=since)
        
        return {
            "http_requests_timeline": self._get_real_requests_timeline(logs, hours),
            "response_times_timeline": self._get_real_response_times_timeline(logs, hours),
            "system_metrics_timeline": self._get_real_system_timeline(hours),
            "error_events": self._get_real_error_events(logs)
        }
    
    def _calculate_real_success_rate(self, http_requests: List[Dict]) -> float:
        """Taxa de sucesso real baseada nos logs"""
        if not http_requests:
            return 1.0
            
        successful = len([req for req in http_requests 
                         if req.get('record', {}).get('extra', {}).get('status_code', 0) < 400])
        
        return successful / len(http_requests)
    
    def _calculate_real_avg_response_time(self, http_requests: List[Dict]) -> float:
        """Tempo médio de resposta real"""
        if not http_requests:
            return 0.0
            
        durations = [req.get('record', {}).get('extra', {}).get('duration_ms', 0) 
                    for req in http_requests]
        
        return sum(durations) / len(durations) if durations else 0.0
    
    def _count_real_active_users(self, logs: List[Dict]) -> int:
        """Conta usuários ativos reais das últimas 24h"""
        user_ids = set()
        
        for log in logs:
            user_id = log.get('record', {}).get('extra', {}).get('user_id')
            if user_id:
                user_ids.add(user_id)
                
        return len(user_ids)
    
    def _calculate_real_error_rate(self, http_requests: List[Dict], error_type: str) -> float:
        """Taxa de erro real baseada nos logs"""
        if not http_requests:
            return 0.0
            
        if error_type == "4xx":
            errors = [req for req in http_requests 
                     if 400 <= req.get('record', {}).get('extra', {}).get('status_code', 0) < 500]
        elif error_type == "5xx":
            errors = [req for req in http_requests 
                     if req.get('record', {}).get('extra', {}).get('status_code', 0) >= 500]
        else:
            return 0.0
            
        return len(errors) / len(http_requests)
    
    def _calculate_real_failed_logins_rate(self, business_events: List[Dict]) -> float:
        """Taxa de login falhado real"""
        login_events = [event for event in business_events 
                       if event.get('record', {}).get('extra', {}).get('event_name') == 'user_login_attempt']
        
        if not login_events:
            return 0.0
            
        failed_logins = [event for event in login_events 
                        if not event.get('record', {}).get('extra', {}).get('context', {}).get('success', True)]
        
        return len(failed_logins) / len(login_events)
    
    def _get_real_requests_timeline(self, logs: List[Dict], hours: int) -> List[Dict]:
        """Timeline real de requisições"""
        http_requests = [log for log in logs 
                        if log.get('record', {}).get('extra', {}).get('event_type') == 'http_request']
        
        hourly_data = defaultdict(lambda: {'count': 0, 'total_duration': 0})
        
        for req in http_requests:
            timestamp = req.get('parsed_timestamp')
            if timestamp:
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour_key]['count'] += 1
                duration = req.get('record', {}).get('extra', {}).get('duration_ms', 0)
                hourly_data[hour_key]['total_duration'] += duration
        
        timeline = []
        for hour, data in sorted(hourly_data.items()):
            avg_response_time = data['total_duration'] / data['count'] if data['count'] > 0 else 0
            timeline.append({
                "timestamp": hour.isoformat(),
                "requests_count": data['count'],
                "avg_response_time": avg_response_time
            })
        
        return timeline
    
    def _get_real_response_times_timeline(self, logs: List[Dict], hours: int) -> List[Dict]:
        """Timeline real de tempos de resposta"""
        http_requests = [log for log in logs 
                        if log.get('record', {}).get('extra', {}).get('event_type') == 'http_request']
        
        hourly_data = defaultdict(list)
        
        for req in http_requests:
            timestamp = req.get('parsed_timestamp')
            if timestamp:
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                duration = req.get('record', {}).get('extra', {}).get('duration_ms', 0)
                hourly_data[hour_key].append(duration)
        
        timeline = []
        for hour, durations in sorted(hourly_data.items()):
            if durations:
                durations.sort()
                p50_idx = int(len(durations) * 0.5)
                p95_idx = int(len(durations) * 0.95)
                p99_idx = int(len(durations) * 0.99)
                
                timeline.append({
                    "timestamp": hour.isoformat(),
                    "p50": durations[p50_idx] if p50_idx < len(durations) else 0,
                    "p95": durations[p95_idx] if p95_idx < len(durations) else 0,
                    "p99": durations[p99_idx] if p99_idx < len(durations) else 0
                })
        
        return timeline
    
    def _get_real_system_timeline(self, hours: int) -> List[Dict]:
        """Timeline real de métricas de sistema do Prometheus"""
        import psutil
        
        current_time = datetime.utcnow()
        timeline = []
        
        timeline.append({
            "timestamp": current_time.isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        })
        
        return timeline
    
    def _get_real_error_events(self, logs: List[Dict]) -> List[Dict]:
        """Eventos de erro reais dos logs"""
        error_events = [log for log in logs 
                       if log.get('record', {}).get('extra', {}).get('event_type') == 'error']
        
        events = []
        for error in error_events:
            extra = error.get('record', {}).get('extra', {})
            events.append({
                "timestamp": error.get('parsed_timestamp', datetime.utcnow()).isoformat(),
                "level": "ERROR",
                "message": extra.get('error_message', 'Unknown error'),
                "error_type": extra.get('error_type', 'Unknown'),
                "context": extra.get('context', {})
            })
        
        return sorted(events, key=lambda x: x["timestamp"], reverse=True)

exporter = MetricsExporter()