"""Middleware de logging para FastAPI.

Este middleware registra todos los requests y responses en el log centralizado.
"""

from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Logger centralizado
from .logger import get_logger

logger = get_logger("invoiceflow.http")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loguea todos los requests HTTP."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()
        request_id = id(request)
        
        # Log request
        logger.info(
            f"[{request_id}] IN: {request.method} {request.url.path} "
            f"| Query: {dict(request.query_params)} "
            f"| Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Calcular duración
            duration = (datetime.now() - start_time).total_seconds()
            
            # Log response
            logger.info(
                f"[{request_id}] OUT: {request.method} {request.url.path} "
                f"-> {response.status_code} ({duration:.3f}s)"
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"[{request_id}] ERROR: {request.method} {request.url.path} "
                f"-> Exception: {str(e)} ({duration:.3f}s)"
            )
            raise
