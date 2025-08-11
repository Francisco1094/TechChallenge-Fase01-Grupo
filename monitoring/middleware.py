from datetime import datetime
import time
import uuid
import asyncio
from functools import wraps
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import json

from .logger import structured_logger
from .metrics import metrics
from .config import MonitoringConfig

class RequestMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware para monitoramento automático de todas as requisições"""
    
    def __init__(self, app, config: Optional[MonitoringConfig] = None):
        super().__init__(app)
        self.config = config or MonitoringConfig()
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")
        ip_address = self._get_client_ip(request)
        
        user_id = await self._extract_user_id(request)
        
        request_body = None
        if (self.config.ENABLE_REQUEST_BODY_LOGGING and 
            method in ['POST', 'PUT', 'PATCH']):
            request_body = await self._get_request_body(request)

        status_code = 500
        response = None
        
        with metrics.track_http_request_in_progress():
            try:
                response = await call_next(request)
                status_code = response.status_code
                
            except Exception as e:
                structured_logger.log_error(
                    error=e,
                    context={"path": path, "method": method},
                    request_id=request_id
                )
                raise
            
            finally:
                duration = time.time() - start_time
    
                metrics.record_http_request(
                    method=method,
                    endpoint=self._normalize_path(path),
                    status_code=status_code,
                    duration=duration
                )
                
                structured_logger.log_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration=duration,
                    user_id=user_id,
                    request_id=request_id,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    request_body=request_body
                )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration*1000:.2f}ms"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai o IP real do cliente"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extrai user_id do token JWT se disponível"""
        try:
            authorization = request.headers.get("authorization")
            if authorization and authorization.startswith("Bearer "):
                # Carlos - Decodificar o JWT para extrair o user_id
                return None
        except Exception:
            pass
        return None
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Extrai o body da requisição para logging"""
        try:
            body = await request.body()
            if len(body) <= self.config.MAX_REQUEST_BODY_SIZE:
                return body.decode('utf-8')[:self.config.MAX_REQUEST_BODY_SIZE]
        except Exception:
            pass
        return None
    
    def _normalize_path(self, path: str) -> str:
        """Normaliza paths com parâmetros para métricas"""
        import re
        normalized = re.sub(r'/\d+', '/{id}', path)
        return normalized


class DatabaseMonitoringMixin:
    """Mixin para instrumentar queries de database"""
    
    @staticmethod
    def monitor_query(table: str, operation: str):
        """Decorator para monitorar queries de database"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    metrics.record_db_query(table, operation, duration)
                    structured_logger.log_database_query(
                        query=f"{operation} on {table}",
                        duration=duration,
                        table=table,
                        operation=operation
                    )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    metrics.record_db_query(table, operation, duration)
                    structured_logger.log_database_query(
                        query=f"{operation} on {table}",
                        duration=duration,
                        table=table,
                        operation=operation
                    )
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator


class BusinessEventTracker:
    """Tracker para eventos de negócio importantes"""
    
    @staticmethod
    def track_book_scraping(books_count: int):
        """Rastreia evento de scraping de livros"""
        for _ in range(books_count):
            metrics.record_business_event("book_scraped")
        
        structured_logger.log_business_event(
            event_name="books_scraped",
            books_count=books_count
        )
    
    @staticmethod
    def track_ml_prediction(recommended: bool, user_id: Optional[str] = None):
        """Rastreia predições de ML"""
        metrics.record_business_event(
            "ml_prediction", 
            recommended=str(recommended).lower()
        )
        
        structured_logger.log_business_event(
            event_name="ml_prediction_made",
            user_id=user_id,
            recommended=recommended
        )
    
    @staticmethod
    def track_user_login(success: bool, username: str):
        """Rastreia tentativas de login"""
        status = "success" if success else "failed"
        metrics.record_business_event("user_login", status=status)
        
        structured_logger.log_business_event(
            event_name="user_login_attempt",
            username=username,
            success=success
        )

    @staticmethod
    def track_scraping_start():
        """Rastreia início do scraping"""
        structured_logger.log_business_event(
            event_name="scraping_started",
            context={
                "source": "books.toscrape.com",
                "start_time": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def track_scraping_progress(page_number: int, books_found: int, total_pages: Optional[int] = None):
        """Rastreia progresso do scraping página por página"""
        
        structured_logger.log_business_event(
            event_name="scraping_page_completed",
            context={
                "page_number": page_number,
                "books_found": books_found,
                "total_pages": total_pages,
                "progress_percent": round((page_number / total_pages) * 100, 2) if total_pages else None
            }
        )

        metrics.record_business_event("page_scraped")

    @staticmethod
    def track_scraping_complete(total_books: int, duration_seconds: float):
        """Rastreia finalização do scraping"""
        structured_logger.log_business_event(
            event_name="scraping_completed",
            context={
                "total_books": total_books,
                "duration_seconds": duration_seconds,
                "books_per_second": round(total_books / duration_seconds, 2),
                "end_time": datetime.utcnow().isoformat()
            }
        )
    