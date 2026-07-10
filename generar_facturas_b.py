"""Genera archivos de muestra con formato FACTURA B real argentina.

Basado en el modelo `ej_fact/factura_b_ejemplo.jpg`.
Genera 5 archivos TXT (uno por proveedor) en `app/data/inbox/`.
"""
import os
import random
from pathlib import Path

OUTPUT_DIR = Path("app/data/inbox")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Datos reales de los proveedores (de suppliers.db)
SUPPLIERS = {
    "SUP001": {
        "razon_social": "TechCorp Argentina SA",
        "cuit": "30-71234567-0",
        "direccion": "Av. Libertador 5000, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-123456-7",
        "inicio_actividades": "01/2015",
        "rubro": "Servicios de desarrollo de software",
        "items_pool": [
            ("Servicio de consultoría técnica hora", 25000.00),
            ("Licencia de software mensual", 45000.00),
            ("Desarrollo feature sprint 2 semanas", 120000.00),
            ("Soporte técnico premium mensual", 35000.00),
            ("Auditoría de código fuente", 80000.00),
        ],
    },
    "SUP002": {
        "razon_social": "Papelería Norte SRL",
        "cuit": "30-69874523-1",
        "direccion": "Av. Cabildo 3000, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-987654-3",
        "inicio_actividades": "05/2010",
        "rubro": "Venta de insumos de oficina",
        "items_pool": [
            ("Resma A4 80gr Caja x 10u", 8500.00),
            ("Cartuchos tinta color original", 12000.00),
            ("Cuaderno universitario x 50u", 15000.00),
            ("Lapiceras microfibra x 100u", 6500.00),
            ("Carpetas A4 carton x 50u", 9000.00),
        ],
    },
    "SUP004": {
        "razon_social": "Limpieza Total SRL",
        "cuit": "30-70555666-7",
        "direccion": "Av. Rivadavia 8500, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-555666-7",
        "inicio_actividades": "02/2018",
        "rubro": "Servicios de limpieza y mantenimiento",
        "items_pool": [
            ("Servicio de limpieza diaria mensual", 65000.00),
            ("Limpieza profunda eventual", 25000.00),
            ("Suministro productos de limpieza", 8000.00),
            ("Limpieza de vidrios en altura", 45000.00),
            ("Desinfección y sanitización", 30000.00),
        ],
    },
    "SUP005": {
        "razon_social": "Consultoría Digital SA",
        "cuit": "30-71234999-2",
        "direccion": "Tucumán 600, Piso 12, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-777888-9",
        "inicio_actividades": "06/2020",
        "rubro": "Consultoría y transformación digital",
        "items_pool": [
            ("Consultoría estratégica hora", 35000.00),
            ("Workshop transformación digital", 450000.00),
            ("Análisis de procesos y propuesta", 180000.00),
            ("Implementación metodología agile", 250000.00),
            ("Mentoring ejecutivo mensual", 380000.00),
        ],
    },
}

RECEPTOR = {
    "razon_social": "EMPRESA DEMO SA",
    "cuit": "30-12345678-9",
    "direccion": "Av. Corrientes 1234, Piso 5",
    "localidad": "CABA (1414)",
    "condicion_iva": "IVA Responsable Inscripto",
}

def format_pesos(n):
    """Formato argentino: 1.234.567,89"""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gen_cae():
    """Genera un CAE-like de 14 dígitos."""
    return "".join(random.choices("0123456789", k=14))

def gen_barcode(cuit, pv, nro, cae, vto):
    """Genera un código de barras similar al formato AFIP (28 dígitos)."""
    # Simplificado: CUIT + PV + tipo + CAE + VTO
    cuit_clean = cuit.replace("-", "")
    return f"{cuit_clean}{pv}0{cae}{vto}"[:28].ljust(28, "0")

def gen_factura_b(supplier_id: str, num: int):
    """Genera una Factura B en formato TXT."""
    sup = SUPPLIERS[supplier_id]
    items = random.sample(sup["items_pool"], k=random.randint(2, 4))

    # Calcular importes
    lineas = []
    subtotal = 0.0
    for i, (desc, precio) in enumerate(items, 1):
        cant = random.randint(1, 3)
        importe = cant * precio
        subtotal += importe
        lineas.append((i, cant, desc, precio, importe))

    # Punto de venta y número
    pv = "0001"
    nro = f"{num:08d}"
    cae = gen_cae()
    vto_ddmmaa = "15012027"
    barcode = gen_barcode(sup["cuit"], pv, nro, cae, vto_ddmmaa)

    factura = f"""================================================================================
                            [FACTURA B]
================================================================================

[EMISOR]
Razon Social:    {sup['razon_social']}
Rubro/Matricula: {sup['rubro']}
Direccion:       {sup['direccion']}
CUIT:            {sup['cuit']}
Ing. Brutos:     {sup['ingresos_brutos']}
Inicio Act.:     {sup['inicio_actividades']}
Condicion IVA:   {sup['condicion_iva']}

================================================================================
CODIGO Nº 06                            FACTURA
                                       Nº {pv} - {nro}
FECHA: 28/06/2026
================================================================================

[RECEPTOR]
Señor/es:     {RECEPTOR['razon_social']}
Dirección:    {RECEPTOR['direccion']}
Localidad:    {RECEPTOR['localidad']}
CUIT:         {RECEPTOR['cuit']}
Condicion IVA: {RECEPTOR['condicion_iva']}

Condiciones de Venta: Contado    [X]
                      Cta. Cte.   [ ]

Remito Nº:    -

================================================================================
CANT.  DESCRIPCION                              P. UNITARIO       IMPORTE
================================================================================
"""
    for i, cant, desc, precio, importe in lineas:
        factura += f"{cant:>4}   {desc:<40} {format_pesos(precio):>14}  {format_pesos(importe):>14}\n"

    factura += f"""================================================================================

                                                            TOTAL $ {format_pesos(subtotal):>14}
================================================================================

[FISCAL]
CAE:          {cae}
Vencimiento:  15/01/2027
Codigo Barras: {barcode}

ORIGINAL BLANCO - DUPLICADO COLOR

--------------------------------------------------------------------------------
Impreso por C5 Digital S.A. - C.U.I.T. 30-71097277-6 Exp. 421836/2010
Fecha de Imp. Diciembre 2016 - Imp. del {pv}-0000001 al {pv}-0000100
www.c5imprenta.com.ar - 4522-0600 lineas rotativas.
--------------------------------------------------------------------------------

              147 "Telefono Gratuito CABA, Area de Defensa
                       y Proteccion al Consumidor".
"""
    return factura


# Generar 5 facturas (1 por proveedor)
contador = 1
for sid in SUPPLIERS:
    for i in range(3):
        filename = f"FC-2026-{sid}-REAL-{i+1:02d}.txt"
        path = OUTPUT_DIR / filename
        content = gen_factura_b(sid, contador)
        path.write_text(content, encoding="utf-8")
        print(f"Generado: {filename} ({len(content)} bytes)")
        contador += 1

# Borrar archivos viejos con formato simple (los que ya no aplican)
print()
print("Archivos en inbox ahora:")
for f in sorted(OUTPUT_DIR.glob("*.txt")):
    print(f"  {f.name} ({f.stat().st_size} bytes)")