"""Tool para extraer datos de facturas PDF."""

from __future__ import annotations

import re
import json
from typing import Optional
from google.adk.tools import ToolContext


def extract_invoice_from_pdf(
    pdf_content: str,
    filename: str = "factura.pdf",
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Extrae datos estructurados de una factura en PDF.
    
    Args:
        pdf_content: Contenido del PDF (base64 o texto extraído)
        filename: Nombre del archivo PDF
        
    Returns:
        dict con los campos extraídos:
        - invoice_id, supplier_id, supplier_name, amount, currency, invoice_date
        - raw_text: texto original extraído
        - extraction_status: "success" | "partial" | "failed"
    """
    try:
        # Si es base64, decodificar primero
        if isinstance(pdf_content, str) and len(pdf_content) > 1000:
            try:
                import base64
                pdf_content = base64.b64decode(pdf_content).decode('utf-8', errors='ignore')
            except Exception:
                pass
        
        # Patrones comunes de facturas argentinas/latinas
        patterns = {
            'invoice_id': [
                r'(?:Factura|N\.?º?|Número|No\.?|Invoice)\s*[:#]?\s*([A-Z0-9\-]+)',
                r'(?:FACTURA|FC|NRO)\s*(?:N\.?º?)?\s*([0-9\-]+)',
            ],
            'supplier_id': [
                r'(?:CUIT|CNPJ|RUC|Tax\s*ID|VAT|Vendor)\s*[:#]?\s*([0-9\-\.]+)',
                r'(?:Proveedor|Proveedor\s*ID|Supplier)\s*[:#]?\s*([A-Z0-9\-]+)',
            ],
            'supplier_name': [
                r'(?:Razón\s*Social|Empresa|Supplier|Empresa\s*Proveedora)\s*[:#]?\s*(.+?)(?:\n|$)',
                r'^(.+?)\s*(?:CUIT|$)',
            ],
            'amount': [
                r'(?:Total|Importe|Total\s*a\s*Pagar|Total\s*Facturado)\s*[$€]?\s*([\d\.,]+)',
                r'(?:\$\s*)?([\d\.]+,\d{2})',
            ],
            'invoice_date': [
                r'(?:Fecha|Factura\s*Fecha|Date)\s*[:#]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
            ],
        }
        
        extracted = {'raw_text': pdf_content[:2000] if len(pdf_content) > 2000 else pdf_content}
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, pdf_content, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    
                    # Limpiar valores
                    if field == 'amount':
                        value = value.replace('.', '').replace(',', '.')
                        try:
                            value = float(value)
                        except:
                            continue
                    elif field == 'invoice_date':
                        # Convertir a formato ISO
                        try:
                            from datetime import datetime
                            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%y']:
                                try:
                                    dt = datetime.strptime(value, fmt)
                                    value = dt.strftime('%Y-%m-%d')
                                    break
                                except:
                                    continue
                        except:
                            pass
                    
                    extracted[field] = value
                    break
        
        # Generar invoice_id si no se encontró
        if 'invoice_id' not in extracted:
            import hashlib
            hash_val = hashlib.md5(pdf_content[:500].encode()).hexdigest()[:8].upper()
            extracted['invoice_id'] = f"INV-{hash_val}"
        
        # Determinar estado de extracción
        required = ['supplier_id', 'amount', 'invoice_date']
        found = sum(1 for f in required if f in extracted)
        
        if found == 3:
            extracted['extraction_status'] = 'success'
        elif found >= 1:
            extracted['extraction_status'] = 'partial'
        else:
            extracted['extraction_status'] = 'failed'
            extracted['reason'] = 'No se pudo extraer información del PDF'
        
        # Guardar en state si está disponible
        if tool_context is not None:
            try:
                tool_context.state.update({
                    'extracted_invoice': extracted,
                    'supplier_id': extracted.get('supplier_id', ''),
                    'supplier_name': extracted.get('supplier_name', ''),
                    'amount': extracted.get('amount', 0),
                    'currency': extracted.get('currency', 'ARS'),
                    'invoice_date': extracted.get('invoice_date', ''),
                    'invoice_id': extracted.get('invoice_id', ''),
                })
            except Exception:
                pass
        
        return extracted
        
    except Exception as e:
        return {
            'extraction_status': 'failed',
            'reason': f'Error extrayendo PDF: {str(e)}',
            'raw_text': ''
        }


# Tool instance para ADK
extract_invoice_tool = extract_invoice_from_pdf


__all__ = ['extract_invoice_from_pdf', 'extract_invoice_tool']
