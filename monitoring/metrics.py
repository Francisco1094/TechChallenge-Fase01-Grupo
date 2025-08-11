import time
import psutil
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from functools import wraps
from contextlib import contextmanager

class MetricsCollector:
    """Coletor de métricas enterprise para APIs"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        
    def _setup_metrics(self):
        """Configura as métricas do Prometheus"""
        
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'HTTP requests currently being processed',
            registry=self.registry
        )
        
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total database queries',
            ['table', 'operation'],
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['table', 'operation'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )
        
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_bytes',
            'System memory usage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage',
            registry=self.registry
        )
        
        self.books_scraped_total = Counter(
            'books_scraped_total',
            'Total books scraped',
            registry=self.registry
        )
        
        self.ml_predictions_total = Counter(
            'ml_predictions_total',
            'Total ML predictions made',
            ['recommended'],
            registry=self.registry
        )
        
        self.user_logins_total = Counter(
            'user_logins_total',
            'Total user logins',
            ['status'],
            registry=self.registry
        )
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Registra métricas de requisição HTTP"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint, 
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @contextmanager
    def track_http_request_in_progress(self):
        """Context manager para rastrear requisições em progresso"""
        self.http_requests_in_progress.inc()
        try:
            yield
        finally:
            self.http_requests_in_progress.dec()
    
    def record_db_query(self, table: str, operation: str, duration: float):
        """Registra métricas de query de database"""
        self.db_queries_total.labels(
            table=table,
            operation=operation
        ).inc()
        
        self.db_query_duration.labels(
            table=table,
            operation=operation
        ).observe(duration)
    
    def update_system_metrics(self):
        """Atualiza métricas do sistema"""

        cpu_percent = psutil.cpu_percent(interval=1)
        self.system_cpu_usage.set(cpu_percent)
        
        memory = psutil.virtual_memory()
        self.system_memory_usage.set(memory.used)

        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.system_disk_usage.set(disk_percent)
    
    def record_business_event(self, event_type: str, **labels):
        """Registra eventos de negócio"""
        if event_type == "book_scraped":
            self.books_scraped_total.inc()
        elif event_type == "ml_prediction":
            recommended = labels.get("recommended", "false")
            self.ml_predictions_total.labels(recommended=recommended).inc()
        elif event_type == "user_login":
            status = labels.get("status", "unknown")
            self.user_logins_total.labels(status=status).inc()
    
    def get_metrics(self) -> str:
        """Retorna métricas no formato Prometheus"""
        self.update_system_metrics()

        raw_metrics = generate_latest(self.registry).decode('utf-8')
        # formatted_metrics = self._format_metrics_with_breaks(raw_metrics)
        formatted_metrics = self._format_metrics_by_category(raw_metrics)

        return formatted_metrics

    # def _format_metrics_with_breaks(self, raw_metrics: str) -> str:
    #     """Formatar métricas com quebras de linha entre seções"""
    #     lines = raw_metrics.strip().split('\n')
    #     formatted_lines = []

    #     previous_metric_name = None

    #     for line in lines:
    #         if not line.strip():
    #             continue

    #         if line.startswith('# HELP'):
    #             metric_name = line.split()[2]
    #             if previous_metric_name and previous_metric_name != metric_name:
    #                 formatted_lines.append('')

    #             previous_metric_name = metric_name

    #         formatted_lines.append(line)

    #     return '\n'.join(formatted_lines) + '\n'

    def _format_metrics_by_category(self, raw_metrics: str) -> str:
        """Organizar métricas por categoria com separadores visuais"""
        lines = raw_metrics.strip().split('\n')
    
        categories = {
            'http_': 'HTTP METRICS',
            'system_': 'SYSTEM METRICS', 
            'db_': 'DATABASE METRICS',
            'books_': 'BUSINESS METRICS (Books)',
            'ml_': 'MACHINE LEARNING METRICS',
            'user_': 'USER METRICS'
        }

        categorized_metrics = {}
        current_section = 'other'

        for line in lines:
            if not line.strip():
                continue

            if line.startswith('# HELP'):
                metric_name = line.split()[2]
                current_section = 'other'

                for prefix, category in categories.items():
                    if metric_name.startswith(prefix):
                        current_section = prefix
                        break
                    
            if current_section not in categorized_metrics:
                categorized_metrics[current_section] = []

            categorized_metrics[current_section].append(line)

        # Montar resultado formatado
        result = []
        result.append("# =" * 40)
        result.append("# FASTAPI MONITORING METRICS")
        result.append("# =" * 40)
        result.append("")

        section_order = ['http_', 'system_', 'db_', 'books_', 'ml_', 'user_', 'other']

        for section in section_order:
            if section in categorized_metrics and categorized_metrics[section]:
                if section in categories:
                    result.append(f"# {'-' * 50}")
                    result.append(f"# {categories[section]}")
                    result.append(f"# {'-' * 50}")
                elif section == 'other':
                    result.append(f"# {'-' * 50}")
                    result.append("# OTHER METRICS")
                    result.append(f"# {'-' * 50}")

                result.append("")

                result.extend(categorized_metrics[section])
                result.append("")

        return '\n'.join(result)

metrics = MetricsCollector()