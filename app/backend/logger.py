"""Configuración centralizada de logging para InvoiceFlow.

Este módulo configura el logging para todo el sistema, guardando en:
- data/logs/invoiceflow.log (archivo)
- stdout/consola
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(project_root: Path, log_level: str = "INFO") -> logging.Logger:
    """Configura el sistema de logging para InvoiceFlow.
    
    Args:
        project_root: Ruta raíz del proyecto
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    # Crear directorio de logs
    log_dir = project_root / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "invoiceflow.log"
    
    # Configurar logger raíz
    logger = logging.getLogger("invoiceflow")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Evitar duplicar handlers si ya está configurado
    if logger.handlers:
        return logger
    
    # Formato de logs
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler para archivo (rotación automática)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Log inicial
    logger.info(f"Logging inicializado. Archivo: {log_file}")
    
    return logger


def get_logger(name: str = "invoiceflow") -> logging.Logger:
    """Obtiene un logger por nombre.
    
    Args:
        name: Nombre del logger (ej: 'invoiceflow.backend', 'invoiceflow.agents')
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


class RequestLoggingMiddleware:
    """Middleware para FastAPI que loguea requests."""
    
    def __init__(self, logger_name: str = "invoiceflow.requests"):
        self.logger = get_logger(logger_name)
    
    async def __call__(self, request, call_next):
        start_time = datetime.now()
        
        # Log request
        self.logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"Response: {request.method} {request.url.path} -> {response.status_code} "
            f"({duration:.3f}s)"
        )
        
        return response


# Logger por defecto
default_logger = None

def init_app_logging(project_root: Path):
    """Inicializa el logging para toda la aplicación."""
    global default_logger
    default_logger = setup_logging(project_root)
    return default_logger
