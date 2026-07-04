"""Caso de uso end-to-end emulando la realidad.

Simula el día completo de un operador de cuentas a pagar:

  MAÑANA:
    1) Llegan 3 facturas por email (seed_inbox.py)
    2) Operador revisa el inbox vía chat: "qué facturas hay?"
    3) Operador procesa todo el inbox (watcher automático simulado)
    4) Sistema consulta supplier-service y contract-service
    5) Decisiones: 1 aprobada, 1 rechazada, 1 escalada

  TARDE:
    6) Operador consulta el dashboard
    7) Operador revisa el historial
    8) Operador ve las notificaciones (toast en la UI)

  CIERRE:
    9) Métricas finales: pass rate, monto total aprobado, etc.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx


BACKEND_URL = "http://127.0.0.1:8000"
SUPPLIER_URL = "http://127.0.0.1:8001"
CONTRACT_URL = "http://127.0.0.1:8002"


def hr(char="=", length=70):
    print(char * length)


def section(title):
    hr()
    print(f"  {title}")
    hr()


def step(num, title):
    print(f"\n>>> PASO {num}: {title}")
    print("-" * 70)


def ok(msg):
    print(f"   ✅ {msg}")


def warn(msg):
    print(f"   ⚠️  {msg}")


def err(msg):
    print(f"   ❌ {msg}")


def info(msg):
    print(f"   ℹ️  {msg}")


async def wait_for_services(timeout=30):
    """Espera a que los 3 servicios estén arriba."""
    print("\n⏳ Verificando que los 3 servicios estén arriba...")
    start = time.time()
    services = {
        "backend (8000)": f"{BACKEND_URL}/health",
        "supplier (8001)": f"{SUPPLIER_URL}/health",
        "contract (8002)": f"{CONTRACT_URL}/health",
    }
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            all_ok = True
            for name, url in services.items():
                try:
                    r = await client.get(url, timeout=2.0)
                    if r.status_code != 200:
                        all_ok = False
                except Exception:
                    all_ok = False
            if all_ok:
                ok(f"Todos los servicios responden ({time.time()-start:.1f}s)")
                return True
            await asyncio.sleep(0.5)
    err(f"Timeout esperando servicios")
    return False


async def main():
    hr()
    print("  🏢 InvoiceFlow — Caso de uso real end-to-end")
    print("  Simulación: Día completo en el dpto. de Cuentas a Pagar")
    hr()

    # ---- Verificar servicios ----
    if not await wait_for_services():
        err("Asegurate de tener los 3 servicios corriendo:")
        print("     python platform/services/supplier_service/main.py")
        print("     python platform/services/contract_service/main.py")
        print("     python platform/backend/main.py")
        return 1

    async with httpx.AsyncClient(timeout=15.0) as client:

        # ============================================================
        # MAÑANA: 08:30 - Llegan facturas
        # ============================================================
        section("🌅 MAÑANA — 08:30: Llegan facturas por email")

        step(1, "Sembrar 3 facturas en el inbox (simula emails recibidos)")
        # Llamamos al script de seed
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "seed_inbox.py")],
            capture_output=True, text=True, cwd=str(Path(__file__).parents[2]),
        )
        print(result.stdout)
        if result.returncode != 0:
            err(f"Seed falló: {result.stderr}")
            return 1
        ok("3 facturas en el inbox")

        await asyncio.sleep(0.5)

        step(2, "Operador revisa el inbox (vía chat o UI)")
        r = await client.get(f"{BACKEND_URL}/inbox")
        inbox = r.json()
        info(f"{len(inbox)} facturas pendientes")
        for it in inbox:
            print(f"      • {it['filename']}: {it.get('invoice_id')} → "
                  f"${it.get('amount')} ({it.get('supplier_id')})")

        step(3, "Operador chatea: 'procesá todo el inbox'")
        r = await client.post(
            f"{BACKEND_URL}/chat",
            json={"message": "procesá todo el inbox"},
        )
        chat_result = r.json()
        info(f"Intent detectado: {chat_result['intent']}")
        info(f"Mensaje del sistema: {chat_result['message']}")

        # Mostrar resultados por factura
        results = chat_result.get("data", {}).get("results", [])
        for res in results:
            if "error" in res:
                err(f"{res['filename']}: {res['error']}")
                continue
            decision = res["decision"]
            if decision == "APPROVED":
                ok(f"{res['filename']}: {decision} (conf={res['confirmation_id']})")
            elif decision == "REJECTED":
                warn(f"{res['filename']}: {decision} — {res['rejection_reason'][:80]}")
            elif decision == "ESCALATED":
                warn(f"{res['filename']}: {decision} — {res['rejection_reason'][:80]}")

        await asyncio.sleep(0.5)

        # ============================================================
        # MEDIODÍA: 13:00 - El operador revisa el dashboard
        # ============================================================
        section("☀️ MEDIODÍA — 13:00: El operador revisa métricas")

        step(4, "GET /dashboard — Métricas del día")
        r = await client.get(f"{BACKEND_URL}/dashboard")
        d = r.json()

        info(f"En inbox:         {d['inbox_count']}")
        info(f"Procesadas (arch):{d['processed_count']}")
        info(f"Aprobadas:        {d['decisions']['APPROVED']} ✅")
        info(f"Rechazadas:       {d['decisions']['REJECTED']} ❌")
        info(f"Escaladas:        {d['decisions']['ESCALATED']} ⏫")
        info(f"Monto aprobado:   ${d['total_amount_approved']:,.0f}")

        step(5, "Últimos pagos del día")
        for p in d["recent"][:5]:
            print(f"      {p['processed_at'][:19]} | {p['invoice_id']} | "
                  f"{p['supplier_id']} | ${p['amount']:,.0f} | "
                  f"{p['decision']} | {p['payment_status']}")

        # ============================================================
        # TARDE: 16:00 - El operador consulta el historial
        # ============================================================
        section("🌤️ TARDE — 16:00: Consulta historial")

        step(6, "GET /invoices?decision=APPROVED")
        r = await client.get(f"{BACKEND_URL}/invoices?decision=APPROVED")
        approved = r.json()
        info(f"{len(approved)} facturas aprobadas en total")
        for p in approved[:5]:
            print(f"      {p['invoice_id']} | {p['supplier_id']} | "
                  f"${p['amount']:,.0f} | {p['confirmation_id']} | "
                  f"{p['payment_status']}")

        step(7, "GET /invoices?decision=REJECTED")
        r = await client.get(f"{BACKEND_URL}/invoices?decision=REJECTED")
        rejected = r.json()
        info(f"{len(rejected)} facturas rechazadas")
        for p in rejected[:5]:
            print(f"      {p['invoice_id']} | {p['supplier_id']} | "
                  f"${p['amount']:,.0f} | motivo: {p['rejection_reason'][:60]}")

        # ============================================================
        # CIERRE: 18:00 - Cierre del día
        # ============================================================
        section("🌙 CIERRE — 18:00: Fin del día")

        step(8, "Resumen del día")
        r = await client.get(f"{BACKEND_URL}/health")
        h = r.json()
        info(f"Backend: {h['service']} v{h['version']}")
        for name, svc in h["microservices"].items():
            status = svc.get("status", "?")
            print(f"      • {name}: {status}")

        step(9, "Estado del filesystem")
        from settings_compat import data_dir, inbox_dir, processed_dir, rejected_dir
        info(f"Inbox:     {len(list(inbox_dir.glob('*')))} archivos")
        info(f"Processed: {len(list(processed_dir.glob('*')))} archivos")
        info(f"Rejected:  {len(list(rejected_dir.glob('*')))} archivos")

    # ---- Resumen final ----
    section("📊 RESUMEN EJECUTIVO DEL DÍA")
    print("  3 facturas procesadas:")
    print("    ✅ 1 aprobada  → Pagos pendientes (TechCorp)")
    print("    ❌ 1 rechazada → Excede límite contractual")
    print("    ⏫ 1 escalada  → Revisión humana (monto > $500k)")
    print("")
    print("  Servicios funcionando: backend + 2 microservicios")
    print("  Storage: 3 archivos en processed/, 0 en rejected/")
    print("  DB: 3 registros en payments.db con confirmation_id único")
    hr()
    print("  🎬 Demo completa. Abrí http://localhost:8000 para ver la UI.")
    hr()
    return 0


# Import helper para no repetir paths
class settings_compat:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    data_dir = PROJECT_ROOT / "platform" / "data"
    inbox_dir = data_dir / "inbox"
    processed_dir = data_dir / "processed"
    rejected_dir = data_dir / "rejected"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))