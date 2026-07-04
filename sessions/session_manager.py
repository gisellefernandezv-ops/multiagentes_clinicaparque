"""Gestión de sesiones por factura.

Wrapper sobre `InMemorySessionService` de Google ADK que mantiene una
sesión independiente por cada factura, con state aislado.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Dict, Optional

from google.adk.sessions import InMemorySessionService, Session


# State inicial de cada sesión (todos los campos que la consigna pide)
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
    # Decisión final
    "decision": "",
    "rejection_reason": "",
    # Metadata
    "guardrail_action": "",
    "guardrail_reason": "",
}


class InvoiceSessionManager:
    """Gestiona el ciclo de vida de una sesión de aprobación de factura.

    Cada factura tiene su propia sesión con state aislado. El state se
    comparte entre el orquestador y los sub-agentes durante la ejecución.

    Uso:
        mgr = InvoiceSessionManager(app_name="invoice_app")
        sid = mgr.create_session(invoice_id="INV-001",
                                 initial={"supplier_id": "SUP001", ...})
        mgr.update_session_state(sid, {"validation_status": "VALID"})
        final = mgr.close_session(sid)
    """

    def __init__(self, app_name: str = "invoice_app"):
        self.app_name = app_name
        self._service = InMemorySessionService()
        # user_id fijo para simplificar (en prod vendría del request)
        self._user_id = "invoice_system"
        # Mapa opcional sid → invoice_id para trazabilidad
        self._invoice_by_sid: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # CRUD de sesiones
    # ------------------------------------------------------------------

    def create_session(
        self,
        invoice_id: str,
        initial: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Crea una nueva sesión, retorna `session_id`.

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
            # Solo aplicar claves conocidas para evitar inyección de campos raros
            for k, v in initial.items():
                if k in INITIAL_STATE:
                    state[k] = v
        state["invoice_id"] = invoice_id

        # Generar un session_id local (lo que devuelve ADK es similar)
        sid = f"sess-{uuid.uuid4().hex[:12]}"

        # Crear la sesión en el service de ADK
        # InMemorySessionService.create_session es async; lo ejecutamos
        # de forma sincrónica usando asyncio.run en su propio loop.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop (p.ej. dentro de adk web), no podemos
                # correr asyncio.run. En ese caso, instanciamos sincrónicamente.
                self._create_session_sync(sid, user_id or self._user_id, state)
            else:
                loop.run_until_complete(
                    self._service.create_session(
                        app_name=self._app_name_safe(),
                        user_id=user_id or self._user_id,
                        session_id=sid,
                        state=state,
                    )
                )
        except RuntimeError:
            # No hay loop en absoluto
            self._create_session_sync(sid, user_id or self._user_id, state)

        self._invoice_by_sid[sid] = invoice_id
        return sid

    def _app_name_safe(self) -> str:
        return self.app_name

    def _create_session_sync(self, sid: str, user_id: str, state: Dict):
        """Crea la sesión en el InMemorySessionService de forma sincrónica.

        ADK no garantiza un constructor sincrónico público; usamos un workaround
        instanciando el Session y empujándolo al dict interno del service.
        """
        session = Session(
            app_name=self.app_name,
            user_id=user_id,
            id=sid,
            state=state,
        )
        # El InMemorySessionService expone `sessions` como dict {(app,user,sid): Session}
        try:
            self._service.sessions[(self.app_name, user_id, sid)] = session
        except Exception:
            # Si la API interna cambia, hacemos fallback a asyncio
            asyncio.run(
                self._service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=sid,
                    state=state,
                )
            )

    def get_session_state(self, session_id: str) -> Dict:
        """Retorna el state actual de la sesión (copia)."""
        session = self._get_session(session_id)
        return dict(session.state)

    def update_session_state(self, session_id: str, updates: Dict) -> None:
        """Actualiza campos del state de la sesión."""
        session = self._get_session(session_id)
        for k, v in updates.items():
            if k in INITIAL_STATE or k in {"confirmation_id", "registered_at"}:
                session.state[k] = v
            else:
                # Aceptar cualquier clave pero loguear (no romper)
                session.state[k] = v

    def close_session(self, session_id: str) -> Dict:
        """Cierra la sesión y retorna el state final."""
        session = self._get_session(session_id)
        final_state = dict(session.state)
        # Limpiar del mapa interno
        self._invoice_by_sid.pop(session_id, None)
        # No eliminamos del service (mantener histórico para auditoría)
        return final_state

    def get_invoice_id(self, session_id: str) -> Optional[str]:
        return self._invoice_by_sid.get(session_id)

    # ------------------------------------------------------------------
    # Service passthrough (para uso con Runner de ADK)
    # ------------------------------------------------------------------

    @property
    def service(self) -> InMemorySessionService:
        """Devuelve el InMemorySessionService subyacente (para pasar a Runner)."""
        return self._service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> Session:
        session = self._service.sessions.get((self.app_name, self._user_id, session_id))
        if session is None:
            raise KeyError(f"Sesión no encontrada: {session_id}")
        return session


__all__ = ["InvoiceSessionManager", "INITIAL_STATE"]


if __name__ == "__main__":
    mgr = InvoiceSessionManager()
    sid = mgr.create_session(
        invoice_id="INV-001",
        initial={"supplier_id": "SUP001", "amount": 50000.0, "invoice_date": "2025-06-01"},
    )
    print(f"Sesión creada: {sid}")

    state = mgr.get_session_state(sid)
    print(f"State inicial: {state}")

    mgr.update_session_state(sid, {"validation_status": "VALID", "contract_status": "WITHIN_LIMIT"})
    state = mgr.get_session_state(sid)
    print(f"State tras updates: {state}")

    final = mgr.close_session(sid)
    print(f"State final: {final}")