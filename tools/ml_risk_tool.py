"""Tool de Evaluación de Riesgo con ML — InvoiceFlow.

Utiliza un modelo de machine learning (regresión logística o árbol de decisión)
para clasificar facturas según su nivel de riesgo.

El modelo considera features como:
- Monto de la factura
- Historial del proveedor (facturas previas, taux de rechazo)
- Antigüedad del proveedor
- Patrones suspectos (fraccionamiento, montos redondos, etc.)

Uso:
    from tools.ml_risk_tool import evaluate_risk_tool
    
    resultado = evaluate_risk_tool(
        supplier_id="SUP001",
        amount=75000,
        invoice_date="2025-06-01",
        invoice_id="FC-001"
    )
"""

from __future__ import annotations

import json
import pickle
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# =============================================================================
# RUTAS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ML_DIR = PROJECT_ROOT / "ml"
RISK_MODEL_PATH = ML_DIR / "risk_model.pkl"
PAYMENTS_DB = PROJECT_ROOT / "data" / "payments.db"

# =============================================================================
# MODELO DE RIESGO POR DEFAULT
# =============================================================================

# Si no existe el modelo entrenado, usamos este modelo simple basado en reglas
# Este modelo se usa también para entrenar el modelo real

DEFAULT_RISK_RULES = {
    # Monto muy alto (> $300k) = riesgo alto
    "monto_alto": {"threshold": 300000, "peso": 0.4},
    # Factura grande respecto al promedio del proveedor
    "monto_anomalo": {"peso": 0.3},
    # Proveedor nuevo (< 6 meses) = riesgo medio
    "proveedor_nuevo": {"dias_minimos": 180, "peso": 0.2},
    # Historial de rechazos
    "historial_rechazos": {"tasa_maxima": 0.3, "peso": 0.5},
    # Posible fraccionamiento (múltiples facturas el mismo día)
    "fraccionamiento": {"facturas_mismo_dia": 2, "peso": 0.4},
}


def _ensure_db():
    """Verifica que la DB exista."""
    return PAYMENTS_DB.exists()


def _load_model():
    """Carga el modelo entrenado desde disco."""
    if not RISK_MODEL_PATH.exists():
        return None

    try:
        with open(RISK_MODEL_PATH, "rb") as f:
            model_data = pickle.load(f)
        return model_data
    except Exception:
        return None


def _save_model(model_data: dict):
    """Guarda el modelo entrenado a disco."""
    ML_DIR.mkdir(parents=True, exist_ok=True)
    with open(RISK_MODEL_PATH, "wb") as f:
        pickle.dump(model_data, f)


# =============================================================================
# FUNCIONES DE EXTRACCIÓN DE FEATURES
# =============================================================================


def get_supplier_age_days(supplier_id: str) -> int:
    """Calcula la antigüedad del proveedor en días."""
    if not _ensure_db():
        return 365  # Default假设proveedor viejo

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT MIN(registered_at) as primera_factura
                FROM payments
                WHERE supplier_id = ?
                """,
                (supplier_id,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                primera = datetime.fromisoformat(row[0].replace("Z", ""))
                return (datetime.now() - primera).days
    except Exception:
        pass

    return 365  # Default: proveedor viejo


def get_supplier_rejection_rate(supplier_id: str, days: int = 90) -> float:
    """Calcula la tasa de rechazo del proveedor en los últimos N días."""
    if not _ensure_db():
        return 0.0

    fecha_limite = (datetime.now() - timedelta(days=days)).isoformat()

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'REJECTED' THEN 1 ELSE 0 END) as rechazadas
                FROM payments
                WHERE supplier_id = ? AND registered_at >= ?
                """,
                (supplier_id, fecha_limite),
            )
            row = cursor.fetchone()
            if row and row[0] > 0:
                return (row[1] or 0) / row[0]
    except Exception:
        pass

    return 0.0


def get_invoices_same_day(supplier_id: str, invoice_date: str) -> int:
    """Cuenta facturas del mismo proveedor en la misma fecha."""
    if not _ensure_db():
        return 0

    try:
        fecha = invoice_date[:10] if len(invoice_date) >= 10 else invoice_date
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM payments
                WHERE supplier_id = ?
                AND DATE(registered_at) = DATE(?)
                AND invoice_id != (
                    SELECT invoice_id FROM payments
                    WHERE supplier_id = ? AND DATE(registered_at) = DATE(?)
                    LIMIT 1
                )
                """,
                (supplier_id, fecha, supplier_id, fecha),
            )
            return cursor.fetchone()[0] or 0
    except Exception:
        return 0


def get_supplier_avg_amount(supplier_id: str) -> float:
    """Obtiene el monto promedio de facturas del proveedor."""
    if not _ensure_db():
        return 0.0

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT AVG(amount) FROM payments
                WHERE supplier_id = ?
                """,
                (supplier_id,),
            )
            result = cursor.fetchone()
            return result[0] or 0.0
    except Exception:
        return 0.0


def get_supplier_total_invoices(supplier_id: str) -> int:
    """Cuenta el total de facturas del proveedor."""
    if not _ensure_db():
        return 0

    try:
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM payments
                WHERE supplier_id = ?
                """,
                (supplier_id,),
            )
            return cursor.fetchone()[0] or 0
    except Exception:
        return 0


def extract_features(supplier_id: str, amount: float, invoice_date: str) -> dict:
    """Extrae todas las features para el modelo de riesgo.

    Args:
        supplier_id: ID del proveedor.
        amount: Monto de la factura.
        invoice_date: Fecha de emisión (ISO format).

    Returns:
        dict con las features extraídas.
    """
    # Features básicas
    features = {
        "monto": amount,
        "monto_log": 0.0,
        "proveedor_antiguedad_dias": 0,
        "proveedor_es_nuevo": 0,
        "tasa_rechazo_90d": 0.0,
        "facturas_mismo_dia": 0,
        "monto_vs_promedio": 1.0,  # ratio: actual / promedio
        "total_facturas_proveedor": 0,
        "es_monto_redondo": 0,  # 1 si termina en 000
    }

    # Calcular features
    features["monto_log"] = 0.0 if amount <= 0 else float(
        __import__("math").log(amount + 1)
    )

    # Antigüedad
    features["proveedor_antiguedad_dias"] = get_supplier_age_days(supplier_id)
    features["proveedor_es_nuevo"] = (
        1 if features["proveedor_antiguedad_dias"] < 180 else 0
    )

    # Tasa de rechazo
    features["tasa_rechazo_90d"] = get_supplier_rejection_rate(supplier_id, 90)

    # Facturas mismo día (posible fraccionamiento)
    features["facturas_mismo_dia"] = get_invoices_same_day(supplier_id, invoice_date)

    # Monto vs promedio
    promedio = get_supplier_avg_amount(supplier_id)
    if promedio > 0:
        features["monto_vs_promedio"] = amount / promedio

    # Total facturas
    features["total_facturas_proveedor"] = get_supplier_total_invoices(supplier_id)

    # Monto redondo (patrón suspecto)
    features["es_monto_redondo"] = 1 if amount > 0 and amount % 1000 == 0 else 0

    return features


def calculate_rule_based_risk(features: dict) -> tuple[str, float, list]:
    """Calcula el riesgo usando reglas heurísticas.

    Returns:
        (nivel_riesgo, score, factores_detectados)
        nivel_riesgo: "bajo" | "medio" | "alto"
        score: 0.0 - 1.0
    """
    score = 0.0
    factores = []

    # Factor 1: Monto alto
    if features["monto"] > 300000:
        score += 0.4
        factores.append({
            "factor": "monto_alto",
            "detalle": f"Monto ${features['monto']:,.0f} > $300.000",
            "peso": 0.4,
        })
    elif features["monto"] > 200000:
        score += 0.2
        factores.append({
            "factor": "monto_medio_alto",
            "detalle": f"Monto ${features['monto']:,.0f} > $200.000",
            "peso": 0.2,
        })

    # Factor 2: Monto anómalo (> 3x el promedio)
    if features["monto_vs_promedio"] > 3.0:
        score += 0.3
        factores.append({
            "factor": "monto_anomalo",
            "detalle": f"Monto {features['monto_vs_promedio']:.1f}x el promedio",
            "peso": 0.3,
        })

    # Factor 3: Proveedor nuevo
    if features["proveedor_es_nuevo"] == 1:
        score += 0.2
        factores.append({
            "factor": "proveedor_nuevo",
            "detalle": f"Proveedor con {features['proveedor_antiguedad_dias']} días",
            "peso": 0.2,
        })

    # Factor 4: Historial de rechazos
    if features["tasa_rechazo_90d"] > 0.3:
        score += 0.5
        factores.append({
            "factor": "historial_rechazos",
            "detalle": f"Tasa rechazo {features['tasa_rechazo_90d']*100:.0f}%",
            "peso": 0.5,
        })
    elif features["tasa_rechazo_90d"] > 0.15:
        score += 0.25
        factores.append({
            "factor": "historial_parcial",
            "detalle": f"Tasa rechazo {features['tasa_rechazo_90d']*100:.0f}%",
            "peso": 0.25,
        })

    # Factor 5: Posible fraccionamiento
    if features["facturas_mismo_dia"] >= 2:
        score += 0.4
        factores.append({
            "factor": "fraccionamiento",
            "detalle": f"{features['facturas_mismo_dia']} facturas mismo día",
            "peso": 0.4,
        })
    elif features["facturas_mismo_dia"] >= 1:
        score += 0.2
        factores.append({
            "factor": "multiples_facturas_dia",
            "detalle": f"{features['facturas_mismo_dia']} factura(s) mismo día",
            "peso": 0.2,
        })

    # Normalizar score a 0-1
    score = min(score, 1.0)

    # Clasificar
    if score >= 0.5:
        nivel = "alto"
    elif score >= 0.25:
        nivel = "medio"
    else:
        nivel = "bajo"

    return nivel, score, factores


# =============================================================================
# FUNCIÓN PRINCIPAL: Evaluar riesgo
# =============================================================================


def evaluate_risk_tool(
    supplier_id: str,
    amount: float,
    invoice_date: str,
    invoice_id: str | None = None,
) -> dict:
    """Evalúa el nivel de riesgo de una factura.

    Utiliza el modelo entrenado si existe, si no, usa reglas heurísticas.

    Args:
        supplier_id: ID del proveedor.
        amount: Monto de la factura.
        invoice_date: Fecha de emisión (YYYY-MM-DD).
        invoice_id: ID de la factura (opcional, para logs).

    Returns:
        dict con:
            - risk_level (str): "bajo" | "medio" | "alto"
            - risk_score (float): score 0.0 - 1.0
            - factores (list): lista de factores de riesgo detectados
            - features (dict): features extraídas
            - model_used (str): "ml" | "rules"
            - recommendation (str): "aprobar" | "revisar" | "escalar"
            - error (str): mensaje de error si lo hubo
    """
    if not supplier_id:
        return {
            "risk_level": "bajo",
            "risk_score": 0.0,
            "factores": [],
            "features": {},
            "model_used": "none",
            "recommendation": "aprobar",
            "error": "supplier_id es obligatorio",
        }

    if amount <= 0:
        return {
            "risk_level": "bajo",
            "risk_score": 0.0,
            "factores": [],
            "features": {},
            "model_used": "none",
            "recommendation": "rechazar",
            "error": "Monto debe ser > 0",
        }

    # Extraer features
    features = extract_features(supplier_id, amount, invoice_date)

    # Intentar usar modelo ML
    model_data = _load_model()
    model_used = "ml"

    if model_data is not None:
        try:
            model = model_data["model"]
            feature_names = model_data.get("feature_names", [])

            # Preparar vector de features
            feature_vector = []
            for fname in feature_names:
                feature_vector.append(features.get(fname, 0.0))

            # Predecir
            import numpy as np

            if hasattr(model, "predict_proba"):
                proba = model.predict_proba([feature_vector])[0]
                # Asumir clase 1 = alto riesgo
                risk_score = float(proba[1]) if len(proba) > 1 else 0.0
            else:
                pred = model.predict([feature_vector])[0]
                risk_score = float(pred)

            # Clasificar según score
            if risk_score >= 0.5:
                risk_level = "alto"
            elif risk_score >= 0.25:
                risk_level = "medio"
            else:
                risk_level = "bajo"

            factores = []

        except Exception as e:
            # Si falla el modelo ML, usar reglas
            model_used = "rules_fallback"
            risk_level, risk_score, factores = calculate_rule_based_risk(features)
    else:
        # Usar reglas heurísticas
        model_used = "rules"
        risk_level, risk_score, factores = calculate_rule_based_risk(features)

    # Determinar recomendación
    if risk_level == "alto":
        recommendation = "escalar"  # Requiere revisión humana
    elif risk_level == "medio":
        recommendation = "revisar"  # puede aprobarse con监控
    else:
        recommendation = "aprobar"  # Aprobación automática

    return {
        "risk_level": risk_level,
        "risk_score": round(risk_score, 4),
        "factores": factores,
        "features": features,
        "model_used": model_used,
        "recommendation": recommendation,
        "error": "",
    }


# =============================================================================
# FUNCIÓN: Entrenar modelo (para evaluación)
# =============================================================================


def train_risk_model_from_data(n_samples: int = 1000) -> dict:
    """Entrena un modelo simple de riesgo con datos de la DB.

    Esta función está pensada para uso en evaluación (tests).
    En producción, el modelo se entrenaría offline.

    Returns:
        dict con resultado del entrenamiento.
    """
    if not _ensure_db():
        return {"success": False, "error": "DB no disponible"}

    try:
        # Recolectar datos de entrenamiento
        with sqlite3.connect(str(PAYMENTS_DB)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM payments
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (n_samples,),
            )
            rows = cursor.fetchall()

        if len(rows) < 10:
            return {"success": False, "error": "Datos insuficientes para entrenar"}

        X = []
        y = []

        for row in rows:
            data = dict(row)
            supplier_id = data["supplier_id"]
            amount = float(data["amount"])
            invoice_date = data.get("registered_at", datetime.now().isoformat())

            features = extract_features(supplier_id, amount, invoice_date)

            # Features para el modelo
            X.append([
                features["monto_log"],
                features["proveedor_antiguedad_dias"] / 365.0,
                features["proveedor_es_nuevo"],
                features["tasa_rechazo_90d"],
                features["facturas_mismo_dia"],
                features["monto_vs_promedio"],
            ])

            # Target: 1 = alto riesgo (REJECTED, ESCALATED)
            decision = data.get("decision", "")
            y.append(1 if decision in ("REJECTED", "ESCALATED") else 0)

        # Entrenar modelo simple
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)

        # Guardar modelo
        model_data = {
            "model": model,
            "feature_names": [
                "monto_log",
                "proveedor_antiguedad_dias_norm",
                "proveedor_es_nuevo",
                "tasa_rechazo_90d",
                "facturas_mismo_dia",
                "monto_vs_promedio",
            ],
            "trained_at": datetime.now().isoformat(),
            "n_samples": len(X),
        }
        _save_model(model_data)

        # Calcular accuracy
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        return {
            "success": True,
            "n_samples": len(X),
            "train_accuracy": round(train_score, 4),
            "test_accuracy": round(test_score, 4),
            "model_path": str(RISK_MODEL_PATH),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ML RISK TOOL — TEST")
    print("=" * 60)

    # Test: Evaluación de riesgo
    print("\n--- Test: Evaluación de riesgo ---")
    result = evaluate_risk_tool(
        supplier_id="SUP001",
        amount=75000,
        invoice_date="2025-06-01",
        invoice_id="FC-TEST-001"
    )
    print(f"  Nivel de riesgo: {result['risk_level']}")
    print(f"  Score: {result['risk_score']}")
    print(f"  Recomendación: {result['recommendation']}")
    print(f"  Modelo usado: {result['model_used']}")
    print(f"  Factores: {result['factores']}")

    # Test: Monto alto
    print("\n--- Test: Monto alto ($600k) ---")
    result = evaluate_risk_tool(
        supplier_id="SUP001",
        amount=600000,
        invoice_date="2025-06-01",
    )
    print(f"  Nivel de riesgo: {result['risk_level']} (score: {result['risk_score']})")

    print("\n✓ Tests completados")
