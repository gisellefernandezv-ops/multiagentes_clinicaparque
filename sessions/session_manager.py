"""Gestion de sesiones por factura.

Wrapper sobre `DatabaseSessionService` de Google ADK que mantiene sesiones
persistentes en SQLite (no se pierden al reiniciar).

Usa la tabla `sessions` y `sessions_state` en adk_sessions.db.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional

from google.adk.sessions import DatabaseSessionService, Session


# Path de la base de datos de sesiones ADK
_SESSIONS_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "adk_sessions.db"


# State inicial de cada sesion (todos los campos que la consigna pide)
INITIAL_STATE: Dict = {
    "invoice_id": "",
    "supplier_id": "",
    "supplier_name": "",
    "amount": 0.0,
    "currency": "ARS",
    "invoice_date": "",
    # Resultados por agente
    "validation_status": "",
    "contract_status": "",
    "contract_limit": 0.0,
    "payment_status": "",
    "confirmation_id": "",
    "registered_at": "",
    # Decision final
    "decision": "",
    "rejection_reason": "",
    # Metadata
    "guardrail_action": "",
    "guardrail_reason": "",
}


def _get_db_url() -> str:
    """Genera la URL de conexion SQLite para SQLAlchemy async (aiosqlite)."""
    db_path = _SESSIONS_DB_PATH
    # Asegurar que el directorio existe
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Usar prefijo sqlite+aiosqlite:// para driver asincrono
    return f"sqlite+aiosqlite:///{str(db_path.resolve())}"


class InvoiceSessionManager:
    """Gestiona el ciclo de vida de una sesion de aprobacion de factura.

    Cada factura tiene su propia sesion con state aislado. El state se
    comparte entre el orquestador y los sub-agentes durante la ejecucion.

    IMPORTANTE: Usa DatabaseSessionService con SQLite para persistencia.
    Las sesiones sobreviven al reinicio del servidor.

    Uso:
        mgr = InvoiceSessionManager(app_name="invoice_app")
        sid = mgr.create_session(invoice_id="INV-001",
                                 initial={"supplier_id": "SUP001", ...})
        mgr.update_session_state(sid, {"validation_status": "VALID"})
        final = mgr.close_session(sid)
    """

    _instance: Optional["InvoiceSessionManager"] = None

    def __init__(self, app_name: str = "invoice_app"):
        self.app_name = app_name
        self._db_url = _get_db_url()
        self._service = DatabaseSessionService(db_url=self._db_url)
        # user_id fijo para simplificar (en prod vendria del request)
        self._user_id = "invoice_system"
        # Mapa opcional sid -> invoice_id para trazabilidad
        self._invoice_by_sid: Dict[str, str] = {}

    @classmethod
    def get_instance(cls, app_name: str = "invoice_app") -> "InvoiceSessionManager":
        """Singleton para evitar crear multiples conexiones."""
        if cls._instance is None:
            cls._instance = cls(app_name)
        return cls._instance

    # ------------------------------------------------------------------
    # CRUD de sesiones
    # ------------------------------------------------------------------

    def create_session(
        self,
        invoice_id: str,
        initial: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Crea una nueva sesion, retorna `session_id`.

        Args:
            invoice_id: ID de la factura (metadata, no se usa en el ID).
            initial: dict con valores iniciales del state.
            user_id: opcional, default "invoice_system".

        Returns:
            session_id (str).
        """
        # Construir state inicial
        state = dict(INITIAL_STATE)
        if initial:
            # Solo aplicar claves conocidas para evitar inyeccion de campos raros
            for k, v in initial.items():
                if k in INITIAL_STATE:
                    state[k] = v
        state["invoice_id"] = invoice_id

        # Generar un session_id local
        sid = f"sess-{uuid.uuid4().hex[:12]}"

        # Crear la sesion en el service de ADK (async)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop, crear tarea asincronica
                future = asyncio.create_task(
                    self._service.create_session(
                        app_name=self.app_name,
                        user_id=user_id or self._user_id,
                        session_id=sid,
                        state=state,
                    )
                )
                # Esperar el resultado
                loop.run_until_complete(future)
            else:
                loop.run_until_complete(
                    self._service.create_session(
                        app_name=self.app_name,
                        user_id=user_id or self._user_id,
                        session_id=sid,
                        state=state,
                    )
                )
        except RuntimeError:
            # No hay loop en absoluto
            asyncio.run(
                self._service.create_session(
                    app_name=self.app_name,
                    user_id=user_id or self._user_id,
                    session_id=sid,
                    state=state,
                )
            )

        self._invoice_by_sid[sid] = invoice_id
        return sid

    def get_session_state(self, session_id: str) -> Dict:
        """Retorna el state actual de la sesion (copia)."""
        session = self._get_session(session_id)
        return dict(session.state)

    def update_session_state(self, session_id: str, updates: Dict) -> None:
        """Actualiza campos del state de la sesion."""
        session = self._get_session(session_id)
        for k, v in updates.items():
            session.state[k] = v
        
        # Persistir el cambio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._service.update_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                        state=session.state,
                    )
                )
            else:
                loop.run_until_complete(
                    self._service.update_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                        state=session.state,
                    )
                )
        except Exception:
            # Si falla la persistencia, al menos mantener en memoria
            pass

    def close_session(self, session_id: str) -> Dict:
        """Cierra la sesion y retorna el state final."""
        session = self._get_session(session_id)
        final_state = dict(session.state)
        # Limpiar del mapa interno
        self._invoice_by_sid.pop(session_id, None)
        return final_state

    def get_invoice_id(self, session_id: str) -> Optional[str]:
        return self._invoice_by_sid.get(session_id)

    # ------------------------------------------------------------------
    # Service passthrough (para uso con Runner de ADK)
    # ------------------------------------------------------------------

    @property
    def service(self) -> DatabaseSessionService:
        """Devuelve el DatabaseSessionService subyacente (para pasar a Runner)."""
        return self._service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> Session:
        """Obtiene una sesion por su ID (async)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.create_task(
                    self._service.get_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                    )
                )
                session = loop.run_until_complete(future)
            else:
                session = loop.run_until_complete(
                    self._service.get_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                    )
                )
        except Exception as e:
            raise KeyError(f"Sesion no encontrada: {session_id}") from e
        
        if session is None:
            raise KeyError(f"Sesion no encontrada: {session_id}")
        return session

    def list_sessions(self, limit: int = 50) -> list:
        """Lista todas las sesiones (para debugging/admin)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.create_task(
                    self._service.list_sessions(
                        app_name=self.app_name,
                        user_id=self._user_id,
                    )
                )
                sessions = loop.run_until_complete(future)
            else:
                sessions = loop.run_until_complete(
                    self._service.list_sessions(
                        app_name=self.app_name,
                        user_id=self._user_id,
                    )
                )
            return list(sessions)[:limit]
        except Exception:
            return []

    def delete_session(self, session_id: str) -> bool:
        """Elimina una sesion (para debugging/admin)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._service.delete_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                    )
                )
            else:
                loop.run_until_complete(
                    self._service.delete_session(
                        app_name=self.app_name,
                        user_id=self._user_id,
                        session_id=session_id,
                    )
                )
            self._invoice_by_sid.pop(session_id, None)
            return True
        except Exception:
            return False


__all__ = ["InvoiceSessionManager", "INITIAL_STATE"]


if __name__ == "__main__":
    print(f"DB Sessions: {_SESSIONS_DB_PATH}")
    print(f"DB URL: {_get_db_url()}")
    
    mgr = InvoiceSessionManager()
    sid = mgr.create_session(
        invoice_id="INV-001",
        initial={"supplier_id": "SUP001", "amount": 50000.0, "invoice_date": "2025-06-01"},
    )
    print(f"Sesion creada: {sid}")

    state = mgr.get_session_state(sid)
    print(f"State inicial: {state}")

    mgr.update_session_state(sid, {"validation_status": "VALID", "contract_status": "WITHIN_LIMIT"})
    state = mgr.get_session_state(sid)
    print(f"State tras updates: {state}")

    final = mgr.close_session(sid)
    print(f"State final: {final}")
    
    print("\nSesiones activas:")
    for s in mgr.list_sessions():
        print(f"  - {s.id}: {s.state.get('invoice_id', 'N/A')}")
