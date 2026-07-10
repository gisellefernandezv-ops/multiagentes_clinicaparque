"""Genera archivos de muestra con tipos FACTURA A, B, C según modelo argentino.

Tipos según AFIP:
  - FACTURA A (cod 01): emisor Responsable Inscripto -> IVA discriminado
  - FACTURA B (cod 06): emisor Responsable Inscripto -> consumidor final (IVA incluido)
  - FACTURA C (cod 11): emisor Monotributo/Exento -> sin IVA

Genera archivos con nomenclatura FC-<punto_venta>-<numero> en `app/data/inbox/`.
"""
import os
import random
from pathlib import Path

OUTPUT_DIR = Path("app/data/inbox")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPLIERS = {
    "SUP001": {
        "razon_social": "TechCorp Argentina SA",
        "cuit": "30-71234567-0",
        "direccion": "Av. Libertador 5000, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-123456-7",
        "inicio_actividades": "01/2015",
        "rubro": "Servicios de desarrollo de software",
    },
    "SUP002": {
        "razon_social": "Papelería Norte SRL",
        "cuit": "30-69874523-1",
        "direccion": "Av. Cabildo 3000, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-987654-3",
        "inicio_actividades": "05/2010",
        "rubro": "Venta de insumos de oficina",
    },
    "SUP004": {
        "razon_social": "Limpieza Total SRL",
        "cuit": "30-70555666-7",
        "direccion": "Av. Rivadavia 8500, CABA",
        "condicion_iva": "IVA Responsable Inscripto",
        "ingresos_brutos": "901-555666-7",
        "inicio_actividades": "02/2018",
        "rubro": "Servicios de limpieza",
    },
    "SUP005": {
        "razon_social": "Consultoría Digital SA",
        "cuit": "30-71234999-2",
        "direccion": "Tucumán 600, Piso 12, CABA",
        "condicion_iva": "Monotributo",
        "ingresos_brutos": "901-777888-9",
        "inicio_actividades": "06/2020",
        "rubro": "Servicios de consultoría",
    },
}

ITEMS_BY_SUPPLIER = {
    "SUP001": [
        ("Servicio de consultoría técnica hora", 25000.00),
        ("Licencia de software mensual", 45000.00),
        ("Desarrollo feature sprint 2 semanas", 120000.00),
        ("Soporte técnico premium mensual", 35000.00),
    ],
    "SUP002": [
        ("Resma A4 80gr Caja x 10u", 8500.00),
        ("Cartuchos tinta color original", 12000.00),
        ("Cuaderno universitario x 50u", 15000.00),
        ("Lapiceras microfibra x 100u", 6500.00),
    ],
    "SUP004": [
        ("Servicio de limpieza diaria mensual", 65000.00),
        ("Limpieza profunda eventual", 25000.00),
        ("Suministro productos de limpieza", 8000.00),
    ],
    "SUP005": [
        ("Consultoría estratégica hora", 35000.00),
        ("Workshop transformación digital", 450000.00),
        ("Análisis de procesos y propuesta", 180000.00),
    ],
}

RECEPTOR = {
    "razon_social": "EMPRESA DEMO SA",
    "cuit": "30-12345678-9",
    "direccion": "Av. Corrientes 1234, Piso 5",
    "localidad": "CABA (1414)",
    "condicion_iva": "IVA Responsable Inscripto",
}

# Tipos de factura: nombre, código AFIP, discrimina_iva
TIPOS = [
    ("A", "01", True),   # Discrimina IVA
    ("B", "06", False),  # IVA incluido
    ("C", "11", False),  # Sin IVA (monotributo)
]

IVA_RATE = 0.21


def format_pesos(n):
    """Formato argentino: 1.234.567,89"""
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gen_cae():
    return "".join(random.choices("0123456789", k=14))


def gen_barcode(cuit, pv, nro, cae, vto):
    cuit_clean = cuit.replace("-", "")
    return f"{cuit_clean}{pv}0{cae}{vto}"[:28].ljust(28, "0")


def gen_factura(supplier_id: str, pv: str, numero: str, tipo: str, codigo: str, discrimina_iva: bool):
    """Genera una Factura A/B/C con la estructura correcta."""
    sup = SUPPLIERS[supplier_id]
    items = random.sample(ITEMS_BY_SUPPLIER[supplier_id], k=random.randint(2, 3))

    lineas = []
    subtotal_sin_iva = 0.0
    for i, (desc, precio_sin_iva) in enumerate(items, 1):
        cant = random.randint(1, 3)
        precio = precio_sin_iva
        # Para tipo B y C el precio mostrado es final (con IVA incluido o sin IVA)
        importe_sin_iva = cant * precio
        subtotal_sin_iva += importe_sin_iva
        lineas.append((i, cant, desc, precio, importe_sin_iva))

    if discrimina_iva:
        # Tipo A: subtotal + IVA 21%
        iva_monto = subtotal_sin_iva * IVA_RATE
        total = subtotal_sin_iva + iva_monto
        # Para tipo A, el precio unitario mostrado NO incluye IVA
        precio_display = "P. UNITARIO (sin IVA)"
        importe_display = "IMPORTE (sin IVA)"
    else:
        iva_monto = 0.0
        total = subtotal_sin_iva
        precio_display = "P. UNITARIO"
        importe_display = "IMPORTE"

    cae = gen_cae()
    vto_ddmmaa = "15012027"
    barcode = gen_barcode(sup["cuit"], pv, numero, cae, vto_ddmmaa)

    # Para tipo C, condicion_venta del emisor es Monotributo
    condicion_emisor = "Monotributo" if tipo == "C" else sup["condicion_iva"]

    factura = f"""================================================================================
                            [FACTURA {tipo}]
================================================================================

[EMISOR]
Razon Social:    {sup['razon_social']}
Rubro/Matricula: {sup['rubro']}
Direccion:       {sup['direccion']}
CUIT:            {sup['cuit']}
Ing. Brutos:     {sup['ingresos_brutos']}
Inicio Act.:     {sup['inicio_actividades']}
Condicion IVA:   {condicion_emisor}

================================================================================
CODIGO Nº {codigo}                          FACTURA {tipo}
                                       Nº {pv} - {numero}
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
CANT.  DESCRIPCION                              {precio_display:>14}  {importe_display:>14}
================================================================================
"""
    for i, cant, desc, precio, importe in lineas:
        factura += f"{cant:>4}   {desc:<40} {format_pesos(precio):>20}  {format_pesos(importe):>20}\n"

    factura += f"""================================================================================
"""
    if discrimina_iva:
        factura += f"""
Subtotal (gravado):                          {format_pesos(subtotal_sin_iva):>20}
IVA 21%:                                     {format_pesos(iva_monto):>20}
                                                            TOTAL $ {format_pesos(total):>20}
"""
    else:
        factura += f"""
                                                            TOTAL $ {format_pesos(total):>20}
"""

    factura += f"""================================================================================

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


# Limpiar archivos viejos (los REAL previos)
print("Limpiando archivos REAL previos...")
for f in OUTPUT_DIR.glob("FC-2026-*-REAL-*.txt"):
    f.unlink()
    print(f"  Deleted: {f.name}")

# Generar nuevas facturas: 2 de cada tipo por proveedor activo
contador_por_tipo = {"A": 0, "B": 0, "C": 0}
pv = "0001"
total_generados = 0
for sid in SUPPLIERS:
    for tipo, codigo, discrimina in TIPOS:
        # Generar 2 de cada tipo
        for i in range(2):
            contador_por_tipo[tipo] += 1
            # Numeración consistente: 8 dígitos
            num = f"{total_generados + 1:08d}"
            # Nombre: FC-<PV>-<NRO>.txt (sin SUP ni REAL)
            filename = f"FC-{pv}-{num}.txt"
            content = gen_factura(sid, pv, num, tipo, codigo, discrimina)
            (OUTPUT_DIR / filename).write_text(content, encoding="utf-8")
            total_generados += 1
            tipo_label = "A (disc.IVA)" if discrimina else ("B (IVA incl)" if tipo == "B" else "C (s/IVA)")
            print(f"  Gen: {filename} - Factura {tipo} - {sid} - {tipo_label}")

print()
print(f"Total generados: {total_generados}")
print(f"Por tipo: A={contador_por_tipo['A']}, B={contador_por_tipo['B']}, C={contador_por_tipo['C']}")
print(f"\nArchivos en inbox ahora:")
for f in sorted(OUTPUT_DIR.glob("*.txt")):
    size = f.stat().st_size
    print(f"  {f.name} ({size} bytes)")