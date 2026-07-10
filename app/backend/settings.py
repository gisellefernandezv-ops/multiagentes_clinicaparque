"""Configuración del backend principal (InvoiceFlow API)."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # URLs de microservicios
    supplier_service_url: str = "http://127.0.0.1:8001"
    contract_service_url: str = "http://127.0.0.1:8002"

    # Watcher
    enable_watcher: bool = True
    watch_interval_seconds: float = 2.0

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Paths
    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "data"

    @property
    def inbox_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "data" / "inbox"

    @property
    def processed_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "data" / "processed"

    @property
    def rejected_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "data" / "rejected"

    @property
    def payments_db(self) -> Path:
        return PROJECT_ROOT / "data" / "payments.db"

    @property
    def frontend_dir(self) -> Path:
        return PROJECT_ROOT / "app" / "frontend"

    model_config = SettingsConfigDict(
        env_prefix="INV_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.inbox_dir.mkdir(parents=True, exist_ok=True)
settings.processed_dir.mkdir(parents=True, exist_ok=True)
settings.rejected_dir.mkdir(parents=True, exist_ok=True)
