import os
from pathlib import Path

# Buscar en múltiples ubicaciones
candidates = [
    "ej_fact/factura_b_ejemplo.jpg",
    "../ej_fact/factura_b_ejemplo.jpg",
    "../../ej_fact/factura_b_ejemplo.jpg",
    "C:/Users/gisel/OneDrive/Escritorio/tp_multiagentes/ej_fact/factura_b_ejemplo.jpg",
    "C:/Users/gisel/OneDrive/Escritorio/tp_multiagentes/invoice_approval_system/ej_fact/factura_b_ejemplo.jpg",
]

for c in candidates:
    p = Path(c)
    print(f"{c}: exists={p.exists()}, size={p.stat().st_size if p.exists() else 'N/A'}")