// ============================================================
// InvoiceApprovalSystem.jsx
// Sistema de Aprobación de Facturas — Frontend React
// Un único archivo, sin TypeScript, sin librerías UI externas.
// ============================================================

import React, { useState, useEffect, useCallback, useRef } from 'react';

// ============================================================
// 1. CONSTANTES — Paleta, fuentes, umbral guardrail
// ============================================================
const COLORS = {
  bg:           '#0F1117',
  surface:      '#1A1D27',
  surface2:     '#222535',
  border:       '#2E3147',
  accent:       '#6C63FF',
  accentSoft:   '#2D2B52',
  approved:     '#22C55E',
  rejected:     '#EF4444',
  escalated:    '#F59E0B',
  pending:      '#6C63FF',
  text:         '#E2E8F0',
  textMuted:    '#64748B',
};

const FONT_SANS = "'Inter', sans-serif";
const FONT_MONO = "'JetBrains Mono', monospace";

const GUARDRAIL_THRESHOLD = 500000;

// Duraciones de simulación (ms)
const TIMINGS = {
  validator: 1500,
  contract:  2000,
  guardrailDelay: 500,   // arranca 500ms después del validador
  guardrail: 1000,
  payment:   1000,
};

// ============================================================
// 2. DATOS MOCK DE PROVEEDORES
// ============================================================
const MOCK_SUPPLIERS = {
  SUP001: {
    name: 'TechCorp SA',
    category: 'Tecnología',
    active: true,
    contractLimit: 150000,
    contractFragment:
      'El proveedor TechCorp SA se compromete a proveer servicios de infraestructura cloud hasta un monto máximo mensual de $150.000 ARS, sujeto a renovación trimestral y cláusulas de nivel de servicio (SLA) del 99,5%.',
  },
  SUP002: {
    name: 'LogiPack SRL',
    category: 'Logística',
    active: true,
    contractLimit: 30000,
    contractFragment:
      'Contrato marco LogiPack: límite operativo mensual $30.000 ARS para servicios de distribución y almacenamiento en CABA y GBA.',
  },
  SUP003: {
    name: 'Distribuidora del Sur',
    category: 'Insumos',
    active: false,
    contractLimit: 0,
    contractFragment: '',
  },
  SUP004: {
    name: 'MarketingPro',
    category: 'Marketing',
    active: true,
    contractLimit: 80000,
    contractFragment:
      'Contrato de servicios de marketing digital. Cupo mensual asignado: $80.000 ARS. Incluye pauta, diseño y community management.',
  },
  SUP005: {
    name: 'Consultores Asociados',
    category: 'Consultoría',
    active: true,
    contractLimit: 200000,
    contractFragment:
      'Contrato de consultoría profesional con tope de facturación de $200.000 ARS por proyecto. Servicios cubiertos: advisory estratégico, auditoría y due diligence.',
  },
};

// ============================================================
// 3. HELPERS
// ============================================================
function formatCurrency(amount) {
  return `$${Number(amount).toLocaleString('es-AR')}`;
}

function formatDate(isoDate) {
  if (!isoDate) return '—';
  // Acepta "YYYY-MM-DD"
  const [y, m, d] = isoDate.split('-');
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

function generateConfirmationId() {
  const now = new Date();
  const y = now.getFullYear();
  const mo = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let suffix = '';
  for (let i = 0; i < 4; i++) {
    suffix += chars[Math.floor(Math.random() * chars.length)];
  }
  return `CONF-${y}${mo}${d}-${suffix}`;
}

function isFutureDate(isoDate) {
  if (!isoDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [y, m, d] = isoDate.split('-').map(Number);
  const picked = new Date(y, m - 1, d);
  return picked > today;
}

// ============================================================
// 4. LÓGICA DE SIMULACIÓN (processInvoice)
// ============================================================
// Devuelve una Promise que se resuelve con { decision, validation, contract, guardrail, payment, confirmationId, rejectionReason, stepsOrder }.
// Llama a callbacks.onStepStart(name) y onStepComplete(name, cardData) para alimentar el panel en tiempo real.
function processInvoice(invoice, callbacks) {
  const { supplier_id, amount, supplier_name } = invoice;
  const supplier = MOCK_SUPPLIERS[supplier_id];
  const result = {
    decision: null,
    confirmationId: null,
    rejectionReason: null,
    steps: {
      validator: null,
      contract:  null,
      guardrail: null,
      payment:   null,
    },
  };

  return new Promise((resolve) => {
    // -------- Agente validador (1.5s) --------
    callbacks.onStepStart?.('validator', 'Consultando base de proveedores...');
    setTimeout(() => {
      if (!supplier) {
        result.steps.validator = {
          status: 'failed',
          title: 'INVÁLIDO',
          body: {
            'Proveedor': supplier_name || '—',
            'ID': supplier_id,
            'Estado en sistema': 'No encontrado',
            'Categoría': '—',
          },
          footer: 'Proveedor no encontrado en el padrón — flujo interrumpido',
        };
      } else if (!supplier.active) {
        result.steps.validator = {
          status: 'failed',
          title: 'INVÁLIDO',
          body: {
            'Proveedor': supplier.name,
            'ID': supplier_id,
            'Estado en sistema': 'Inactivo',
            'Categoría': supplier.category,
          },
          footer: 'Proveedor inactivo — flujo interrumpido',
        };
      } else {
        result.steps.validator = {
          status: 'completed',
          title: 'VÁLIDO',
          body: {
            'Proveedor': supplier.name,
            'ID': supplier_id,
            'Estado en sistema': 'Activo',
            'Categoría': supplier.category,
          },
          footer: 'Proveedor verificado — continuando al siguiente paso',
        };
      }
      callbacks.onStepComplete?.('validator', result.steps.validator);

      // Si falló la validación, cortar
      if (result.steps.validator.status === 'failed') {
        result.decision = 'REJECTED';
        result.rejectionReason = !supplier
          ? 'Proveedor no encontrado en el padrón'
          : 'Proveedor inactivo en el sistema';
        return resolve(result);
      }

      // -------- Control de contrato (2s) en paralelo con Guardrail --------
      callbacks.onStepStart?.('contract', 'Buscando límite contractual...');

      // Guardrail arranca 0.5s después del inicio del contrato
      const guardrailStartTimer = setTimeout(() => {
        callbacks.onStepStart?.('guardrail', 'Evaluando umbral de seguridad...');
        setTimeout(() => {
          if (amount > GUARDRAIL_THRESHOLD) {
            result.steps.guardrail = {
              status: 'escalated',
              title: 'ESCALADO',
              body: {
                'Monto de factura': formatCurrency(amount),
                'Umbral guardrail': formatCurrency(GUARDRAIL_THRESHOLD),
                'Excedente': formatCurrency(amount - GUARDRAIL_THRESHOLD),
              },
              footer: 'Monto excede el umbral autónomo — escalada a revisión humana',
            };
          } else {
            result.steps.guardrail = {
              status: 'completed',
              title: 'DENTRO DEL UMBRAL',
              body: {
                'Monto de factura': formatCurrency(amount),
                'Umbral guardrail': formatCurrency(GUARDRAIL_THRESHOLD),
                'Margen disponible': formatCurrency(GUARDRAIL_THRESHOLD - amount),
              },
              footer: 'Monto dentro del umbral autónomo',
            };
          }
          callbacks.onStepComplete?.('guardrail', result.steps.guardrail);
        }, TIMINGS.guardrail);
      }, TIMINGS.guardrailDelay);

      // Contrato termina a los 2s
      setTimeout(() => {
        if (amount > supplier.contractLimit) {
          const excedente = amount - supplier.contractLimit;
          result.steps.contract = {
            status: 'failed',
            title: 'SUPERA LÍMITE',
            body: {
              'Límite contractual': formatCurrency(supplier.contractLimit),
              'Monto de factura': formatCurrency(amount),
              'Excedente': formatCurrency(excedente),
            },
            footer: 'Factura rechazada — se detiene el proceso',
          };
        } else {
          result.steps.contract = {
            status: 'completed',
            title: 'DENTRO DEL LÍMITE',
            body: {
              'Límite contractual': formatCurrency(supplier.contractLimit),
              'Monto de factura': formatCurrency(amount),
              'Disponible': formatCurrency(supplier.contractLimit - amount),
              'Fragmento del contrato': supplier.contractFragment,
            },
            footer: 'Límite contractual verificado — autorizando registro',
          };
        }
        callbacks.onStepComplete?.('contract', result.steps.contract);

        // Guardrail tiene prioridad: si escaló, no importa el resto (per spec)
        if (result.steps.guardrail && result.steps.guardrail.status === 'escalated') {
          clearTimeout(guardrailStartTimer);
          result.decision = 'ESCALATED';
          result.rejectionReason = 'Monto superior a $500.000 requiere aprobación humana';
          return resolve(result);
        }

        // Si falló el contrato, cortar
        if (result.steps.contract.status === 'failed') {
          clearTimeout(guardrailStartTimer);
          result.decision = 'REJECTED';
          result.rejectionReason = `El monto ${formatCurrency(amount)} supera el límite contractual de ${formatCurrency(supplier.contractLimit)}`;
          return resolve(result);
        }

        // -------- Registro de pago (1s) --------
        callbacks.onStepStart?.('payment', 'Registrando pago en base de datos...');
        setTimeout(() => {
          const confirmationId = generateConfirmationId();
          const now = new Date().toLocaleString('es-AR');
          result.steps.payment = {
            status: 'completed',
            title: 'REGISTRADO',
            body: {
              'Nro. de confirmación': confirmationId,
              'Estado de pago': 'Pendiente',
              'Fecha de registro': now,
            },
            footer: 'Pago registrado en el sistema — pendiente de ejecución',
          };
          callbacks.onStepComplete?.('payment', result.steps.payment);
          result.decision = 'APPROVED';
          result.confirmationId = confirmationId;
          resolve(result);
        }, TIMINGS.payment);
      }, TIMINGS.contract);
    }, TIMINGS.validator);
  });
}

// ============================================================
// 5. ICONOS (inline SVG para portabilidad)
// ============================================================
const Icon = ({ name, size = 18, color = 'currentColor' }) => {
  const props = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: color, strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (name) {
    case 'shield':
      return (<svg {...props}><path d="M12 2 4 5v7c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V5l-8-3Z" /></svg>);
    case 'document':
      return (<svg {...props}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M8 13h8M8 17h6" /></svg>);
    case 'lock':
      return (<svg {...props}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>);
    case 'database':
      return (<svg {...props}><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v6c0 1.7 4 3 9 3s9-1.3 9-3V5" /><path d="M3 11v6c0 1.7 4 3 9 3s9-1.3 9-3v-6" /></svg>);
    case 'check':
      return (<svg {...props}><path d="M5 12l4 4L19 7" /></svg>);
    case 'cross':
      return (<svg {...props}><path d="M6 6l12 12M18 6L6 18" /></svg>);
    case 'alert':
      return (<svg {...props}><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.73 3h16.92a2 2 0 0 0 1.73-3L13.7 3.86a2 2 0 0 0-3.4 0Z" /></svg>);
    case 'arrow':
      return (<svg {...props}><path d="M5 12h14M13 6l6 6-6 6" /></svg>);
    case 'restart':
      return (<svg {...props}><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /></svg>);
    case 'spinner':
      return (<svg {...props} style={{ animation: 'spin 1s linear infinite' }}><path d="M21 12a9 9 0 1 1-6.2-8.55" /></svg>);
    case 'pulse':
      return (<svg {...props}><path d="M3 12h4l3-9 4 18 3-9h4" /></svg>);
    case 'folder':
      return (<svg {...props}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>);
    case 'x':
      return (<svg {...props}><path d="M18 6L6 18M6 6l12 12" /></svg>);
    default:
      return null;
  }
};

// ============================================================
// 6. ESTILOS GLOBALES (inyectados vía <style>)
// ============================================================
const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

.ias-root {
  font-family: ${FONT_SANS};
  background: ${COLORS.bg};
  color: ${COLORS.text};
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.ias-root *, .ias-root *::before, .ias-root *::after { box-sizing: border-box; }

@keyframes spin      { from { transform: rotate(0deg); }   to { transform: rotate(360deg); } }
@keyframes fadeIn    { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fillLine  { from { height: 0%; }                to { height: 100%; } }
@keyframes dotPulse  { 0%,100% { opacity: 1; } 50% { opacity: 0.4; transform: scale(1.15); } }
@keyframes slideDown { from { opacity: 0; max-height: 0; }  to { opacity: 1; max-height: 600px; } }

/* ----- HEADER ----- */
.ias-header {
  background: ${COLORS.surface};
  border-bottom: 1px solid ${COLORS.border};
  padding: 18px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ias-header-title  { font-size: 18px; font-weight: 600; color: ${COLORS.text}; letter-spacing: -0.2px; }
.ias-header-sub    { font-size: 12px; color: ${COLORS.textMuted}; margin-top: 2px; }
.ias-header-brand  { display: flex; flex-direction: column; }
.ias-header-logoWrap{ display:flex; align-items:center; gap: 12px; }
.ias-header-logo   {
  width: 36px; height: 36px; border-radius: 8px;
  background: ${COLORS.accent}; display: grid; place-items: center; color: white;
}
.ias-health {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 14px; border-radius: 999px;
  background: ${COLORS.surface2}; border: 1px solid ${COLORS.border};
  font-size: 12px; color: ${COLORS.text};
}
.ias-health-dot {
  width: 8px; height: 8px; border-radius: 50%; background: ${COLORS.approved};
  animation: dotPulse 1.6s ease-in-out infinite;
}

/* ----- HEADER BUTTONS ----- */
.ias-header-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px;
  background: ${COLORS.surface2};
  border: 1px solid ${COLORS.border};
  border-radius: 8px;
  color: ${COLORS.text};
  font-size: 13px; font-weight: 500;
  font-family: ${FONT_SANS};
  cursor: pointer;
  transition: all 0.15s;
}
.ias-header-btn:hover { background: ${COLORS.border}; }
.ias-header-btn-accent { background: ${COLORS.accentSoft}; border-color: ${COLORS.accent}; color: ${COLORS.accent}; }
.ias-header-btn-accent:hover { background: ${COLORS.accent}; color: white; }

/* ----- MODAL ----- */
.ias-modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}
.ias-modal {
  background: ${COLORS.surface};
  border: 1px solid ${COLORS.border};
  border-radius: 16px;
  width: 90%; max-width: 800px;
  max-height: 80vh;
  overflow: hidden;
  display: flex; flex-direction: column;
  animation: fadeIn 0.3s ease-out;
}
.ias-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid ${COLORS.border};
  display: flex; justify-content: space-between; align-items: center;
}
.ias-modal-title { font-size: 18px; font-weight: 600; }
.ias-modal-close {
  background: none; border: none;
  color: ${COLORS.textMuted};
  cursor: pointer; padding: 8px;
  border-radius: 6px;
  transition: all 0.15s;
}
.ias-modal-close:hover { background: ${COLORS.surface2}; color: ${COLORS.text}; }
.ias-modal-body { padding: 24px; overflow-y: auto; flex: 1; }
.ias-modal-footer {
  padding: 16px 24px;
  border-top: 1px solid ${COLORS.border};
  display: flex; justify-content: flex-end; gap: 10px;
}

/* ----- INVOICE LIST ----- */
.ias-invoice-list { display: flex; flex-direction: column; gap: 12px; }
.ias-invoice-item {
  background: ${COLORS.bg};
  border: 1px solid ${COLORS.border};
  border-radius: 10px;
  padding: 16px;
  display: grid; grid-template-columns: 1fr auto; gap: 12px;
  align-items: center;
}
.ias-invoice-item:hover { border-color: ${COLORS.accent}; }
.ias-invoice-info { display: flex; flex-direction: column; gap: 4px; }
.ias-invoice-name { font-weight: 600; font-size: 14px; }
.ias-invoice-meta { font-size: 12px; color: ${COLORS.textMuted}; }
.ias-invoice-actions { display: flex; gap: 8px; }
.ias-invoice-btn {
  padding: 6px 12px;
  background: ${COLORS.surface2};
  border: 1px solid ${COLORS.border};
  border-radius: 6px;
  color: ${COLORS.text};
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.ias-invoice-btn:hover { background: ${COLORS.border}; }
.ias-invoice-btn-view { color: ${COLORS.accent}; border-color: ${COLORS.accent}; }
.ias-invoice-btn-view:hover { background: ${COLORS.accentSoft}; }

/* ----- GROUPE R RESULT ----- */
.ias-grouper-result {
  background: ${COLORS.bg};
  border: 1px solid ${COLORS.border};
  border-radius: 12px;
  padding: 24px;
  margin-top: 16px;
}
.ias-grouper-result h4 { font-size: 14px; margin-bottom: 12px; color: ${COLORS.text}; }
.ias-grouper-stat { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; }
.ias-grouper-folder {
  background: ${COLORS.surface2};
  border: 1px solid ${COLORS.border};
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
}
.ias-grouper-folder-title { font-weight: 600; font-size: 13px; margin-bottom: 4px; }
.ias-grouper-folder-files { font-size: 12px; color: ${COLORS.textMuted}; }

/* ----- LAYOUT ----- */
.ias-main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px 32px 64px;
  display: grid;
  gap: 24px;
}
.ias-row { display: grid; grid-template-columns: 380px 1fr; gap: 24px; align-items: flex-start; }
@media (max-width: 1100px) { .ias-row { grid-template-columns: 1fr; } }

/* ----- CARD GENÉRICA ----- */
.ias-card {
  background: ${COLORS.surface};
  border: 1px solid ${COLORS.border};
  border-radius: 12px;
  padding: 24px;
}
.ias-card-title {
  font-size: 13px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.8px; color: ${COLORS.textMuted}; margin-bottom: 18px;
}

/* ----- FORMULARIO ----- */
.ias-form-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.ias-label      { font-size: 12px; font-weight: 500; color: ${COLORS.text}; display: flex; justify-content: space-between; align-items: center; }
.ias-label-req  { color: ${COLORS.rejected}; margin-left: 4px; }
.ias-input, .ias-select {
  background: ${COLORS.bg};
  border: 1px solid ${COLORS.border};
  color: ${COLORS.text};
  border-radius: 8px;
  padding: 10px 12px;
  font-family: ${FONT_SANS};
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
  width: 100%;
}
.ias-input::placeholder { color: ${COLORS.textMuted}; }
.ias-input:focus, .ias-select:focus { border-color: ${COLORS.accent}; background: ${COLORS.surface2}; }
.ias-input.has-error     { border-color: ${COLORS.rejected}; }
.ias-input-prefix-wrap  { position: relative; }
.ias-input-prefix       {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  color: ${COLORS.textMuted}; font-family: ${FONT_MONO}; font-size: 14px; pointer-events: none;
}
.ias-input-prefix-wrap .ias-input { padding-left: 28px; font-family: ${FONT_MONO}; }
.ias-error-msg { color: ${COLORS.rejected}; font-size: 11px; margin-top: 4px; }
.ias-warn-msg  { color: ${COLORS.escalated}; font-size: 12px; margin-top: 6px; padding: 8px 10px; background: rgba(245, 158, 11, 0.08); border-radius: 6px; border-left: 2px solid ${COLORS.escalated}; }

.ias-submit {
  width: 100%;
  background: ${COLORS.accent};
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  font-family: ${FONT_SANS};
  cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: background 0.15s, transform 0.05s;
  margin-top: 8px;
}
.ias-submit:hover:not(:disabled) { background: #5b53e6; }
.ias-submit:active:not(:disabled){ transform: translateY(1px); }
.ias-submit:disabled { background: ${COLORS.surface2}; color: ${COLORS.textMuted}; cursor: not-allowed; }

.ias-supplier-hint {
  margin-top: 18px; padding: 12px;
  background: ${COLORS.surface2}; border-radius: 8px; border: 1px dashed ${COLORS.border};
  font-size: 12px; color: ${COLORS.textMuted};
}
.ias-supplier-hint strong { color: ${COLORS.text}; display: block; margin-bottom: 6px; font-weight: 600; }
.ias-supplier-hint code   { font-family: ${FONT_MONO}; color: ${COLORS.accent}; font-size: 11px; }

/* ----- TIMELINE (signature element) ----- */
.ias-process-panel {
  background: ${COLORS.surface};
  border: 1px solid ${COLORS.border};
  border-radius: 12px;
  padding: 28px;
}
.ias-process-empty { text-align: center; padding: 60px 20px; color: ${COLORS.textMuted}; font-size: 14px; }
.ias-process-grid  { display: grid; grid-template-columns: 220px 1fr; gap: 32px; }
@media (max-width: 900px) { .ias-process-grid { grid-template-columns: 1fr; } }

.ias-timeline { position: relative; padding-left: 8px; }
.ias-timeline-node {
  position: relative;
  display: flex; align-items: center; gap: 14px;
  padding: 10px 0;
  min-height: 56px;
}
.ias-timeline-icon {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: grid; place-items: center;
  background: ${COLORS.surface2};
  border: 2px solid ${COLORS.border};
  color: ${COLORS.textMuted};
  flex-shrink: 0;
  z-index: 2;
  transition: all 0.3s;
}
.ias-timeline-icon.running   { background: ${COLORS.accentSoft}; border-color: ${COLORS.accent}; color: ${COLORS.accent}; }
.ias-timeline-icon.completed { background: rgba(34, 197, 94, 0.15); border-color: ${COLORS.approved}; color: ${COLORS.approved}; }
.ias-timeline-icon.failed    { background: rgba(239, 68, 68, 0.15); border-color: ${COLORS.rejected}; color: ${COLORS.rejected}; }
.ias-timeline-icon.escalated { background: rgba(245, 158, 11, 0.15); border-color: ${COLORS.escalated}; color: ${COLORS.escalated}; }

.ias-timeline-label   { font-size: 13px; font-weight: 500; color: ${COLORS.textMuted}; transition: color 0.3s; }
.ias-timeline-label.completed { color: ${COLORS.text}; }
.ias-timeline-label.failed    { color: ${COLORS.rejected}; }
.ias-timeline-label.escalated { color: ${COLORS.escalated}; }
.ias-timeline-label.running   { color: ${COLORS.text}; }

.ias-timeline-connector {
  width: 2px;
  height: 20px;
  margin: -4px 0 -4px 25px;            /* overlap con bordes de los íconos para continuidad visual */
  background: ${COLORS.border};
  transition: background 0.3s;
  border-radius: 1px;
  position: relative;
  overflow: hidden;
}
.ias-timeline-connector::after {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0; bottom: 0;
  background: ${COLORS.accent};
  transform: scaleY(0);
  transform-origin: bottom;
  transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s;
}
.ias-timeline-connector.fill-running::after {
  background: linear-gradient(to bottom, ${COLORS.accent} 0%, ${COLORS.border} 100%);
  transform: scaleY(1);
  animation: scrollGradient 1.4s linear infinite;
}
.ias-timeline-connector.fill-completed::after { transform: scaleY(1); background: ${COLORS.accent}; }
.ias-timeline-connector.fill-failed          { background: ${COLORS.rejected}; }
.ias-timeline-connector.fill-failed::after   { display: none; }
.ias-timeline-connector.fill-escalated       { background: ${COLORS.escalated}; }
.ias-timeline-connector.fill-escalated::after { display: none; }

@keyframes scrollGradient {
  from { background-position: 0 -100%; }
  to   { background-position: 0 100%; }
}

/* ----- AGENT CARD ----- */
.ias-agent-list { display: flex; flex-direction: column; gap: 14px; }
.ias-agent-card {
  background: ${COLORS.bg};
  border: 1px solid ${COLORS.border};
  border-radius: 10px;
  padding: 16px 18px;
  animation: fadeIn 0.35s ease-out;
}
.ias-agent-card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px;
}
.ias-agent-card-title { font-size: 14px; font-weight: 600; color: ${COLORS.text}; display: flex; align-items: center; gap: 8px; }
.ias-agent-card-body  { font-size: 13px; color: ${COLORS.text}; margin-bottom: 10px; }
.ias-agent-card-body dl { display: grid; grid-template-columns: 160px 1fr; gap: 6px 12px; }
.ias-agent-card-body dt { color: ${COLORS.textMuted}; font-size: 12px; }
.ias-agent-card-body dd { color: ${COLORS.text}; font-size: 13px; }
.ias-agent-card-body dd.ias-mono {
  font-family: ${FONT_MONO}; font-size: 12px;
  background: ${COLORS.surface2}; padding: 8px 10px; border-radius: 6px;
  border-left: 2px solid ${COLORS.accent}; color: ${COLORS.text};
  font-style: italic;
  grid-column: 1 / -1;
}
.ias-agent-card-body dd.ias-mono-empty { color: ${COLORS.textMuted}; }
.ias-agent-card-body .ias-running-msg { color: ${COLORS.accent}; display: flex; align-items: center; gap: 8px; font-size: 13px; }
.ias-agent-card-footer {
  font-size: 12px;
  color: ${COLORS.textMuted};
  padding-top: 10px;
  border-top: 1px solid ${COLORS.border};
  font-style: italic;
}
.ias-agent-card-footer.completed { color: ${COLORS.approved}; font-style: normal; }
.ias-agent-card-footer.failed    { color: ${COLORS.rejected}; font-style: normal; }
.ias-agent-card-footer.escalated { color: ${COLORS.escalated}; font-style: normal; }

/* ----- BADGES ----- */
.ias-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;
  font-family: ${FONT_SANS};
}
.ias-badge.completed { background: rgba(34, 197, 94, 0.15);  color: ${COLORS.approved};  border: 1px solid rgba(34, 197, 94, 0.3); }
.ias-badge.failed    { background: rgba(239, 68, 68, 0.15);  color: ${COLORS.rejected};  border: 1px solid rgba(239, 68, 68, 0.3); }
.ias-badge.escalated { background: rgba(245, 158, 11, 0.15); color: ${COLORS.escalated}; border: 1px solid rgba(245, 158, 11, 0.3); }
.ias-badge.running   { background: rgba(108, 99, 255, 0.15); color: ${COLORS.accent};    border: 1px solid rgba(108, 99, 255, 0.3); }
.ias-badge.pending   { background: ${COLORS.surface2};        color: ${COLORS.textMuted}; border: 1px solid ${COLORS.border}; }

/* ----- RESULTADO FINAL ----- */
.ias-final-card {
  background: ${COLORS.surface};
  border: 1px solid ${COLORS.border};
  border-radius: 12px;
  padding: 28px;
  border-left: 4px solid ${COLORS.border};
  position: relative;
  overflow: hidden;
  animation: fadeIn 0.4s ease-out;
}
.ias-final-card.approved  { border-left-color: ${COLORS.approved}; }
.ias-final-card.rejected  { border-left-color: ${COLORS.rejected}; }
.ias-final-card.escalated { border-left-color: ${COLORS.escalated}; }

.ias-final-head   { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.ias-final-icon   {
  width: 52px; height: 52px; border-radius: 12px;
  display: grid; place-items: center; flex-shrink: 0;
}
.ias-final-icon.approved  { background: rgba(34, 197, 94, 0.15);  color: ${COLORS.approved}; }
.ias-final-icon.rejected  { background: rgba(239, 68, 68, 0.15);  color: ${COLORS.rejected}; }
.ias-final-icon.escalated { background: rgba(245, 158, 11, 0.15); color: ${COLORS.escalated}; }
.ias-final-title     { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }
.ias-final-subtitle  { font-size: 13px; color: ${COLORS.textMuted}; margin-top: 2px; }
.ias-final-confirmation {
  font-family: ${FONT_MONO}; font-size: 15px;
  color: ${COLORS.accent};
  background: ${COLORS.accentSoft};
  padding: 10px 14px; border-radius: 8px;
  margin-bottom: 20px; display: inline-block;
}
.ias-final-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
@media (max-width: 700px) { .ias-final-summary { grid-template-columns: repeat(2, 1fr); } }
.ias-final-summary-cell { background: ${COLORS.bg}; border: 1px solid ${COLORS.border}; border-radius: 8px; padding: 12px; }
.ias-final-summary-label { font-size: 11px; color: ${COLORS.textMuted}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.ias-final-summary-value { font-size: 15px; color: ${COLORS.text}; font-weight: 600; }
.ias-final-summary-value.ias-mono { font-family: ${FONT_MONO}; font-size: 13px; }
.ias-final-reason {
  background: rgba(239, 68, 68, 0.08);
  border-left: 3px solid ${COLORS.rejected};
  padding: 12px 14px; border-radius: 6px;
  color: #fca5a5; font-size: 13px;
  margin-bottom: 20px;
}
.ias-final-action { display: flex; justify-content: flex-end; }
.ias-btn-secondary {
  background: ${COLORS.surface2}; color: ${COLORS.text};
  border: 1px solid ${COLORS.border};
  border-radius: 8px; padding: 10px 18px;
  font-size: 13px; font-weight: 500;
  font-family: ${FONT_SANS};
  cursor: pointer;
  display: inline-flex; align-items: center; gap: 8px;
  transition: all 0.15s;
}
.ias-btn-secondary:hover { background: ${COLORS.border}; }

/* ----- HISTORIAL ----- */
.ias-history { background: ${COLORS.surface}; border: 1px solid ${COLORS.border}; border-radius: 12px; padding: 24px; }
.ias-history-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.ias-history-empty {
  text-align: center; padding: 40px 20px;
  color: ${COLORS.textMuted}; font-size: 13px;
}
.ias-history-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ias-history-table th {
  text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
  color: ${COLORS.textMuted}; font-weight: 600;
  padding: 10px 12px; border-bottom: 1px solid ${COLORS.border};
}
.ias-history-table td {
  padding: 12px 12px;
  border-bottom: 1px solid ${COLORS.border};
  color: ${COLORS.text};
}
.ias-history-table tr:last-child td { border-bottom: none; }
.ias-history-table tr.ias-row-clickable { cursor: pointer; transition: background 0.15s; }
.ias-history-table tr.ias-row-clickable:hover { background: ${COLORS.surface2}; }
.ias-row-mono { font-family: ${FONT_MONO}; font-size: 12px; color: ${COLORS.textMuted}; }
.ias-row-detail {
  background: ${COLORS.bg};
  padding: 0;
}
.ias-row-detail-inner {
  padding: 16px 18px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  animation: slideDown 0.25s ease-out;
}
.ias-row-detail-inner h5 {
  grid-column: 1 / -1;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.5px;
  color: ${COLORS.textMuted}; margin-bottom: 4px;
}
.ias-row-detail-inner dl { display: grid; grid-template-columns: 130px 1fr; gap: 4px 12px; font-size: 12px; }
.ias-row-detail-inner dt { color: ${COLORS.textMuted}; }
.ias-row-detail-inner dd { color: ${COLORS.text}; font-family: ${FONT_MONO}; font-size: 12px; }
`;

// ============================================================
// 7. SUB-COMPONENTES
// ============================================================

// --- Header ---
function Header({ onShowInvoices, onRunGrouper }) {
  return (
    <header className="ias-header" role="banner">
      <div className="ias-header-logoWrap">
        <div className="ias-header-logo">
          <Icon name="pulse" size={20} color="white" />
        </div>
        <div className="ias-header-brand">
          <div className="ias-header-title">Sistema de Aprobación de Facturas</div>
          <div className="ias-header-sub">Powered by agentes de IA</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <button
          className="ias-header-btn"
          onClick={onShowInvoices}
          title="Ver todas las facturas"
        >
          <Icon name="document" size={16} color="currentColor" />
          Ver facturas
        </button>
        <button
          className="ias-header-btn ias-header-btn-accent"
          onClick={onRunGrouper}
          title="Ejecutar agente agrupador"
        >
          <Icon name="folder" size={16} color="currentColor" />
          Agrupar facturas
        </button>
        <div className="ias-health" role="status" aria-live="polite">
          <span className="ias-health-dot" />
          <span>Sistema operativo</span>
        </div>
      </div>
    </header>
  );
}

// --- InvoiceForm ---
function InvoiceForm({ onSubmit, disabled, initialData, onReset }) {
  const [form, setForm] = useState(initialData || {
    invoice_id: '',
    supplier_id: '',
    supplier_name: '',
    amount: '',
    currency: 'ARS',
    invoice_date: new Date().toISOString().slice(0, 10),
  });
  const [touched, setTouched] = useState({});

  // Resetear cuando cambia initialData (botón "Nueva factura")
  useEffect(() => {
    if (initialData) setForm(initialData);
  }, [initialData]);

  const errors = {
    invoice_id: !form.invoice_id.trim() ? 'Requerido' : null,
    supplier_id: !form.supplier_id.trim() ? 'Requerido' : null,
    supplier_name: !form.supplier_name.trim() ? 'Requerido' : null,
    amount: !form.amount ? 'Requerido' : (Number(form.amount) <= 0 ? 'Debe ser mayor a 0' : null),
    invoice_date: !form.invoice_date ? 'Requerido' : (isFutureDate(form.invoice_date) ? 'No puede ser futura' : null),
  };
  const isValid = Object.values(errors).every(e => !e);

  const handleChange = (field, value) => {
    setForm(f => ({ ...f, [field]: value }));
  };
  const handleBlur = (field) => setTouched(t => ({ ...t, [field]: true }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isValid || disabled) return;
    onSubmit({
      ...form,
      amount: Number(form.amount),
    });
  };

  const amountNum = Number(form.amount) || 0;
  const showGuardrailWarn = amountNum > GUARDRAIL_THRESHOLD;

  return (
    <div className="ias-card" role="region" aria-label="Formulario de ingreso de factura">
      <div className="ias-card-title">Nueva factura</div>
      <form onSubmit={handleSubmit} noValidate>
        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-invoice_id">
            Nro. de factura <span className="ias-label-req">*</span>
          </label>
          <input
            id="ias-invoice_id"
            className={`ias-input ${touched.invoice_id && errors.invoice_id ? 'has-error' : ''}`}
            type="text"
            placeholder="INV-2025-001"
            value={form.invoice_id}
            onChange={e => handleChange('invoice_id', e.target.value)}
            onBlur={() => handleBlur('invoice_id')}
            disabled={disabled}
            aria-required="true"
          />
          {touched.invoice_id && errors.invoice_id && <div className="ias-error-msg">{errors.invoice_id}</div>}
        </div>

        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-supplier_id">
            ID de proveedor <span className="ias-label-req">*</span>
          </label>
          <input
            id="ias-supplier_id"
            className={`ias-input ${touched.supplier_id && errors.supplier_id ? 'has-error' : ''}`}
            type="text"
            placeholder="SUP001"
            value={form.supplier_id}
            onChange={e => handleChange('supplier_id', e.target.value.toUpperCase())}
            onBlur={() => handleBlur('supplier_id')}
            disabled={disabled}
            aria-required="true"
          />
          {touched.supplier_id && errors.supplier_id && <div className="ias-error-msg">{errors.supplier_id}</div>}
        </div>

        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-supplier_name">
            Nombre del proveedor <span className="ias-label-req">*</span>
          </label>
          <input
            id="ias-supplier_name"
            className={`ias-input ${touched.supplier_name && errors.supplier_name ? 'has-error' : ''}`}
            type="text"
            placeholder="TechCorp SA"
            value={form.supplier_name}
            onChange={e => handleChange('supplier_name', e.target.value)}
            onBlur={() => handleBlur('supplier_name')}
            disabled={disabled}
            aria-required="true"
          />
          {touched.supplier_name && errors.supplier_name && <div className="ias-error-msg">{errors.supplier_name}</div>}
        </div>

        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-amount">
            Monto <span className="ias-label-req">*</span>
          </label>
          <div className="ias-input-prefix-wrap">
            <span className="ias-input-prefix">$</span>
            <input
              id="ias-amount"
              className={`ias-input ${touched.amount && errors.amount ? 'has-error' : ''}`}
              type="number"
              placeholder="150000"
              value={form.amount}
              onChange={e => handleChange('amount', e.target.value)}
              onBlur={() => handleBlur('amount')}
              disabled={disabled}
              min="1"
              aria-required="true"
            />
          </div>
          {touched.amount && errors.amount && <div className="ias-error-msg">{errors.amount}</div>}
          {showGuardrailWarn && (
            <div className="ias-warn-msg" role="note">
              ⚠ Montos superiores a $500.000 requieren aprobación humana
            </div>
          )}
        </div>

        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-currency">
            Moneda <span className="ias-label-req">*</span>
          </label>
          <select
            id="ias-currency"
            className="ias-select"
            value={form.currency}
            onChange={e => handleChange('currency', e.target.value)}
            disabled={disabled}
            aria-required="true"
          >
            <option value="ARS">ARS</option>
            <option value="USD">USD</option>
          </select>
        </div>

        <div className="ias-form-field">
          <label className="ias-label" htmlFor="ias-invoice_date">
            Fecha de emisión <span className="ias-label-req">*</span>
          </label>
          <input
            id="ias-invoice_date"
            className={`ias-input ${touched.invoice_date && errors.invoice_date ? 'has-error' : ''}`}
            type="date"
            value={form.invoice_date}
            onChange={e => handleChange('invoice_date', e.target.value)}
            onBlur={() => handleBlur('invoice_date')}
            disabled={disabled}
            aria-required="true"
          />
          {touched.invoice_date && errors.invoice_date && <div className="ias-error-msg">{errors.invoice_date}</div>}
        </div>

        <button
          type="submit"
          className="ias-submit"
          disabled={!isValid || disabled}
          aria-disabled={!isValid || disabled}
        >
          {disabled ? (
            <>
              <Icon name="spinner" size={16} color="currentColor" /> Procesando...
            </>
          ) : (
            <>Iniciar aprobación <Icon name="arrow" size={16} color="currentColor" /></>
          )}
        </button>
      </form>

      <div className="ias-supplier-hint">
        <strong>Proveedores de prueba</strong>
        SUP001 (límite $150k) · SUP002 ($30k) · SUP003 (inactivo) ·
        SUP004 ($80k) · SUP005 ($200k) · <code>SUP999</code> (no existe)
      </div>
    </div>
  );
}

// --- ProgressLine (línea vertical signature) ---
function ProgressLine({ stepStates }) {
  const steps = [
    { key: 'validator', label: 'Agente validador',    icon: 'shield' },
    { key: 'contract',  label: 'Control de contrato', icon: 'document' },
    { key: 'guardrail', label: 'Guardrail',           icon: 'lock' },
    { key: 'payment',   label: 'Registro de pago',    icon: 'database' },
  ];

  return (
    <div className="ias-timeline" role="list" aria-label="Progreso del flujo de aprobación">
      {steps.map((s, idx) => {
        const state = stepStates[s.key] || 'pending';
        const isLast = idx === steps.length - 1;
        // El conector entre este nodo y el siguiente se colorea según el ESTADO DE ESTE nodo
        // (si este nodo se completó, la línea hacia abajo se "llena").
        let connectorClass = '';
        if (state === 'completed') connectorClass = 'fill-completed';
        else if (state === 'failed')    connectorClass = 'fill-failed';
        else if (state === 'escalated') connectorClass = 'fill-escalated';
        else if (state === 'running')   connectorClass = 'fill-running';

        return (
          <React.Fragment key={s.key}>
            <div className="ias-timeline-node" role="listitem">
              <div
                className={`ias-timeline-icon ${state}`}
                aria-label={`${s.label}: ${state}`}
                role="img"
              >
                {state === 'pending'   ? null : (
                  state === 'running'   ? <Icon name="spinner" size={16} color="currentColor" /> :
                  state === 'failed'    ? <Icon name="cross"   size={16} color="currentColor" /> :
                  state === 'escalated' ? <Icon name="alert"   size={16} color="currentColor" /> :
                                          <Icon name="check"   size={16} color="currentColor" />
                )}
              </div>
              <div className={`ias-timeline-label ${state}`}>{s.label}</div>
            </div>
            {!isLast && <div className={`ias-timeline-connector ${connectorClass}`} aria-hidden="true" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// --- AgentCard ---
function AgentCard({ name, status, body, runningMessage }) {
  // status: 'pending' | 'running' | 'completed' | 'failed' | 'escalated'
  // Si todavía no empezó, no se muestra la card (aparece con fade-in al iniciarse, según spec).
  if (status === 'pending') return null;

  const isRunning = status === 'running';
  const fields = (body && body.body) || {};

  // Determinar si el valor va en fuente mono (JetBrains Mono) según la clave
  const isMonoKey = (key) => {
    const k = key.toLowerCase();
    return k.includes('fragmento') || k.includes('confirmación') || k.includes('contrato');
  };

  return (
    <div className="ias-agent-card" role="article" aria-live="polite">
      <div className="ias-agent-card-header">
        <div className="ias-agent-card-title">{name}</div>
        {isRunning ? (
          <span className="ias-badge running">
            <Icon name="spinner" size={11} color="currentColor" /> En proceso
          </span>
        ) : (
          <span className={`ias-badge ${status}`}>
            <Icon
              name={status === 'failed' ? 'cross' : status === 'escalated' ? 'alert' : 'check'}
              size={11}
              color="currentColor"
            />
            {body.title || status}
          </span>
        )}
      </div>

      <div className="ias-agent-card-body">
        {isRunning ? (
          <div className="ias-running-msg">
            <Icon name="spinner" size={14} color="currentColor" />
            {runningMessage || 'Procesando...'}
          </div>
        ) : (
          <dl>
            {Object.entries(fields).map(([k, v]) => (
              <React.Fragment key={k}>
                <dt>{k}</dt>
                <dd className={isMonoKey(k) ? 'ias-mono' : ''}>{v}</dd>
              </React.Fragment>
            ))}
          </dl>
        )}
      </div>

      {body && body.footer && !isRunning && (
        <div className={`ias-agent-card-footer ${status}`}>{body.footer}</div>
      )}
    </div>
  );
}

// --- FinalResult ---
function FinalResult({ result, invoice, onReset }) {
  if (!result) return null;
  const { decision, confirmationId, rejectionReason } = result;
  const decisionClass = decision === 'APPROVED' ? 'approved' : decision === 'REJECTED' ? 'rejected' : 'escalated';

  const titles = {
    APPROVED:  { title: 'Factura aprobada',            sub: 'Pendiente de pago', icon: 'check' },
    REJECTED:  { title: 'Factura rechazada',           sub: 'No se procesará el pago', icon: 'cross' },
    ESCALATED: { title: 'Escalada a revisión humana',  sub: 'Requiere aprobación manual', icon: 'alert' },
  };
  const t = titles[decision];

  return (
    <div className={`ias-final-card ${decisionClass}`} role="alert">
      <div className="ias-final-head">
        <div className={`ias-final-icon ${decisionClass}`}>
          <Icon name={t.icon} size={28} color="currentColor" />
        </div>
        <div>
          <div className="ias-final-title">{t.title}</div>
          <div className="ias-final-subtitle">{t.sub}</div>
        </div>
      </div>

      {(decision === 'APPROVED' && confirmationId) && (
        <div className="ias-final-confirmation" aria-label="Número de confirmación">
          {confirmationId}
        </div>
      )}

      <div className="ias-final-summary">
        <div className="ias-final-summary-cell">
          <div className="ias-final-summary-label">Factura</div>
          <div className="ias-final-summary-value">{invoice.invoice_id}</div>
        </div>
        <div className="ias-final-summary-cell">
          <div className="ias-final-summary-label">Proveedor</div>
          <div className="ias-final-summary-value">{invoice.supplier_name}</div>
        </div>
        <div className="ias-final-summary-cell">
          <div className="ias-final-summary-label">Monto</div>
          <div className="ias-final-summary-value ias-mono">{formatCurrency(invoice.amount)} {invoice.currency}</div>
        </div>
        <div className="ias-final-summary-cell">
          <div className="ias-final-summary-label">Fecha</div>
          <div className="ias-final-summary-value">{formatDate(invoice.invoice_date)}</div>
        </div>
      </div>

      {(decision === 'REJECTED' || decision === 'ESCALATED') && rejectionReason && (
        <div className="ias-final-reason">
          <strong>Motivo: </strong>{rejectionReason}
        </div>
      )}

      <div className="ias-final-action">
        <button type="button" className="ias-btn-secondary" onClick={onReset}>
          <Icon name="restart" size={14} color="currentColor" /> Nueva factura
        </button>
      </div>
    </div>
  );
}

// --- InvoiceHistory ---
function InvoiceHistory({ history }) {
  const [expanded, setExpanded] = useState(null);

  if (history.length === 0) {
    return (
      <div className="ias-history" role="region" aria-label="Historial de facturas">
        <div className="ias-history-head">
          <div className="ias-card-title" style={{ margin: 0 }}>Historial de la sesión</div>
        </div>
        <div className="ias-history-empty">Aún no hay facturas procesadas en esta sesión.</div>
      </div>
    );
  }

  const formatTime = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return iso; }
  };

  return (
    <div className="ias-history" role="region" aria-label="Historial de facturas">
      <div className="ias-history-head">
        <div className="ias-card-title" style={{ margin: 0 }}>Historial de la sesión</div>
        <div style={{ fontSize: 12, color: COLORS.textMuted }}>{history.length} factura{history.length !== 1 ? 's' : ''}</div>
      </div>
      <table className="ias-history-table">
        <thead>
          <tr>
            <th>Nro. Factura</th>
            <th>Proveedor</th>
            <th>Monto</th>
            <th>Resultado</th>
            <th>Confirmación</th>
            <th>Hora</th>
          </tr>
        </thead>
        <tbody>
          {history.slice().reverse().map((h, i) => {
            const realIdx = history.length - 1 - i;
            const isOpen = expanded === realIdx;
            const decisionClass = h.result.decision === 'APPROVED' ? 'completed' : h.result.decision === 'REJECTED' ? 'failed' : 'escalated';
            return (
              <React.Fragment key={realIdx}>
                <tr
                  className="ias-row-clickable"
                  onClick={() => setExpanded(isOpen ? null : realIdx)}
                  aria-expanded={isOpen}
                >
                  <td><strong>{h.invoice.invoice_id}</strong></td>
                  <td>{h.invoice.supplier_name}</td>
                  <td className="ias-mono">{formatCurrency(h.invoice.amount)} {h.invoice.currency}</td>
                  <td>
                    <span className={`ias-badge ${decisionClass}`}>
                      {h.result.decision === 'APPROVED' ? 'Aprobada' : h.result.decision === 'REJECTED' ? 'Rechazada' : 'Escalada'}
                    </span>
                  </td>
                  <td className="ias-row-mono">{h.result.confirmationId || '—'}</td>
                  <td className="ias-row-mono">{formatTime(h.processedAt)}</td>
                </tr>
                {isOpen && (
                  <tr className="ias-row-detail">
                    <td colSpan={6}>
                      <div className="ias-row-detail-inner">
                        <h5>Detalle del proceso</h5>
                        {h.result.steps.validator && (
                          <>
                            <dl>
                              <dt>Validador</dt><dd>{h.result.steps.validator.status}</dd>
                              {h.result.steps.validator.body['Estado en sistema'] && (<><dt>Estado</dt><dd>{h.result.steps.validator.body['Estado en sistema']}</dd></>)}
                            </dl>
                            {h.result.steps.contract && (
                              <dl>
                                <dt>Contrato</dt><dd>{h.result.steps.contract.status}</dd>
                                {h.result.steps.contract.body['Límite contractual'] && (<><dt>Límite</dt><dd>{h.result.steps.contract.body['Límite contractual']}</dd></>)}
                              </dl>
                            )}
                            {h.result.steps.guardrail && (
                              <dl>
                                <dt>Guardrail</dt><dd>{h.result.steps.guardrail.status}</dd>
                              </dl>
                            )}
                            {h.result.steps.payment && (
                              <dl>
                                <dt>Pago</dt><dd>{h.result.steps.payment.status}</dd>
                              </dl>
                            )}
                          </>
                        )}
                        {h.result.rejectionReason && (
                          <dl style={{ gridColumn: '1 / -1' }}>
                            <dt>Motivo</dt><dd>{h.result.rejectionReason}</dd>
                          </dl>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// --- InvoiceModal ---
function InvoiceModal({ isOpen, onClose, invoices, onViewInvoice, grouperResult, onRunGrouper, isRunningGrouper }) {
  if (!isOpen) return null;

  return (
    <div className="ias-modal-overlay" onClick={onClose}>
      <div className="ias-modal" onClick={e => e.stopPropagation()}>
        <div className="ias-modal-header">
          <div className="ias-modal-title">Gestión de Facturas</div>
          <button className="ias-modal-close" onClick={onClose}>
            <Icon name="x" size={20} />
          </button>
        </div>
        <div className="ias-modal-body">
          {invoices.length === 0 ? (
            <div className="ias-history-empty">
              <Icon name="folder" size={32} color={COLORS.textMuted} />
              <p style={{ marginTop: 12 }}>No hay facturas pendientes en la carpeta new invoices.</p>
            </div>
          ) : (
            <>
              <p style={{ marginBottom: 16, color: COLORS.textMuted, fontSize: 13 }}>
                Facturas pendientes en la carpeta "new invoices": {invoices.length}
              </p>
              <div className="ias-invoice-list">
                {invoices.map((inv, idx) => (
                  <div key={idx} className="ias-invoice-item">
                    <div className="ias-invoice-info">
                      <div className="ias-invoice-name">{inv.filename}</div>
                      <div className="ias-invoice-meta">
                        {inv.supplier_id ? `Proveedor: ${inv.supplier_id}` : 'Proveedor no identificado'} · {inv.size_kb} KB
                      </div>
                    </div>
                    <div className="ias-invoice-actions">
                      <button className="ias-invoice-btn ias-invoice-btn-view" onClick={() => onViewInvoice(inv)}>
                        Ver
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {grouperResult && (
            <div className="ias-grouper-result">
              <h4>Resultado del Agente Agrupador</h4>
              <div className="ias-grouper-stat">
                <Icon name="check" size={16} color={COLORS.approved} />
                <span>Facturas movidas: {grouperResult.moved_count}</span>
              </div>
              {grouperResult.grouped_by_cuit && Object.keys(grouperResult.grouped_by_cuit).length > 0 && (
                <>
                  <h4 style={{ marginTop: 12 }}>Carpetas creadas:</h4>
                  {Object.entries(grouperResult.grouped_by_cuit).map(([cuit, files]) => (
                    <div key={cuit} className="ias-grouper-folder">
                      <div className="ias-grouper-folder-title">CUIT-{cuit}</div>
                      <div className="ias-grouper-folder-files">
                        {Array.isArray(files) ? files.join(', ') : 'Archivos movidos'}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
        <div className="ias-modal-footer">
          <button className="ias-btn-secondary" onClick={onClose}>
            Cerrar
          </button>
          <button
            className="ias-submit"
            onClick={onRunGrouper}
            disabled={isRunningGrouper}
            style={{ marginTop: 0, width: 'auto' }}
          >
            {isRunningGrouper ? (
              <><Icon name="spinner" size={16} color="currentColor" /> Procesando...</>
            ) : (
              <><Icon name="folder" size={16} color="currentColor" /> Ejecutar Agente Agrupador</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// --- InvoiceDetailModal ---
function InvoiceDetailModal({ invoice, onClose }) {
  if (!invoice) return null;

  return (
    <div className="ias-modal-overlay" onClick={onClose}>
      <div className="ias-modal" onClick={e => e.stopPropagation()}>
        <div className="ias-modal-header">
          <div className="ias-modal-title">{invoice.filename}</div>
          <button className="ias-modal-close" onClick={onClose}>
            <Icon name="x" size={20} />
          </button>
        </div>
        <div className="ias-modal-body">
          <pre style={{ fontSize: 12, color: COLORS.text, whiteSpace: 'pre-wrap', fontFamily: FONT_MONO }}>
            {invoice.content || 'Contenido no disponible'}
          </pre>
        </div>
        <div className="ias-modal-footer">
          <button className="ias-btn-secondary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// 8. COMPONENTE PRINCIPAL
// ============================================================
function InvoiceApprovalSystem() {
  // Estados del flujo
  const [flow, setFlow] = useState('idle'); // idle | processing | completed | error
  const [currentInvoice, setCurrentInvoice] = useState(null);
  const [stepStates, setStepStates] = useState({
    validator: 'pending',
    contract:  'pending',
    guardrail: 'pending',
    payment:   'pending',
  });
  const [agentCards, setAgentCards] = useState({});
  const [runningMessages, setRunningMessages] = useState({});
  const [finalResult, setFinalResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [initialFormData, setInitialFormData] = useState(null);

  // Estados del modal de facturas
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [grouperResult, setGrouperResult] = useState(null);
  const [isRunningGrouper, setIsRunningGrouper] = useState(false);

  // Inyectar fuentes de Google en <head>
  useEffect(() => {
    const id = 'ias-google-fonts';
    if (document.getElementById(id)) return;
    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap';
    document.head.appendChild(link);
  }, []);

  // --- Callbacks del processInvoice ---
  const handleStepStart = useCallback((name, message) => {
    setStepStates(prev => ({ ...prev, [name]: 'running' }));
    setRunningMessages(prev => ({ ...prev, [name]: message }));
    setAgentCards(prev => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  const handleStepComplete = useCallback((name, cardData) => {
    setStepStates(prev => ({ ...prev, [name]: cardData.status }));
    setAgentCards(prev => ({ ...prev, [name]: cardData }));
    setRunningMessages(prev => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  // --- Mostrar modal de facturas ---
  const handleShowInvoices = useCallback(async () => {
    setShowInvoiceModal(true);
    setGrouperResult(null);
    
    // Simular carga de facturas (en producción vendría del backend)
    // Aquí usamos datos mock para demostración
    const mockInvoices = [
      { filename: 'FC-2026-SUP001-NUEVA-1.txt', supplier_id: 'SUP001', size_kb: 2.3, path: 'new invoices/FC-2026-SUP001-NUEVA-1.txt' },
      { filename: 'FC-2026-SUP001-NUEVA-2.txt', supplier_id: 'SUP001', size_kb: 2.1, path: 'new invoices/FC-2026-SUP001-NUEVA-2.txt' },
      { filename: 'FC-2026-SUP002-NUEVA-1.txt', supplier_id: 'SUP002', size_kb: 2.5, path: 'new invoices/FC-2026-SUP002-NUEVA-1.txt' },
      { filename: 'FC-2026-SUP003-NUEVA-1.txt', supplier_id: 'SUP003', size_kb: 2.0, path: 'new invoices/FC-2026-SUP003-NUEVA-1.txt' },
    ];
    setInvoices(mockInvoices);
  }, []);

  // --- Ver detalle de factura ---
  const handleViewInvoice = useCallback((invoice) => {
    // Simular contenido (en producción vendría del backend)
    const mockContent = `
================================================================================
                              FACTURA A
================================================================================

Numero: ${invoice.filename.replace('.txt', '')}
Fecha: ${new Date().toLocaleDateString('es-AR')}
Vencimiento: ${new Date(Date.now() + 30*24*60*60*1000).toLocaleDateString('es-AR')}

--------------------------------------------------------------------------------
EMPRESA EMISORA                         PROVEEDOR
--------------------------------------------------------------------------------
TechCorp Argentina SA                   TechCorp SA
Av. Libertador 5000                     CUIT: 30-71234567-0
CABA, Argentina                         Av. Corrientes 1234, CABA
                                        info@techcorp.com

--------------------------------------------------------------------------------
DETALLE DE LA FACTURA
--------------------------------------------------------------------------------
Servicio de consultoria mensual         $ 20.661.16    $ 4.338.84    $    25,000.00
                                                                                           
--------------------------------------------------------------------------------
                              SUBTOTAL: $ 20.661.16
                              IVA 21%:  $  4.338.84
================================================================================
                              TOTAL: ARS $    25,000.00
================================================================================
`;
    setSelectedInvoice({ ...invoice, content: mockContent });
  }, []);

  // --- Ejecutar agente agrupador ---
  const handleRunGrouper = useCallback(async () => {
    setIsRunningGrouper(true);
    
    // Simular ejecución del agente agrupador
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const result = {
      success: true,
      message: 'Agrupacion completada',
      moved_count: 4,
      grouped_by_cuit: {
        '30712345670': ['FC-2026-SUP001-NUEVA-1.txt', 'FC-2026-SUP001-NUEVA-2.txt'],
        '30698745231': ['FC-2026-SUP002-NUEVA-1.txt'],
        '30701112223': ['FC-2026-SUP003-NUEVA-1.txt'],
      }
    };
    
    setGrouperResult(result);
    setIsRunningGrouper(false);
    setInvoices([]); // Limpiar lista al agrupar
  }, []);

  // --- Submit del formulario ---
  const handleSubmit = useCallback(async (invoice) => {
    setCurrentInvoice(invoice);
    setFlow('processing');
    setFinalResult(null);
    setStepStates({ validator: 'pending', contract: 'pending', guardrail: 'pending', payment: 'pending' });
    setAgentCards({});
    setRunningMessages({});

    try {
      const result = await processInvoice(invoice, {
        onStepStart: handleStepStart,
        onStepComplete: handleStepComplete,
      });
      setFinalResult(result);
      setFlow('completed');
      setHistory(h => [...h, { invoice, result, processedAt: new Date().toISOString() }]);
    } catch (e) {
      console.error('Error en el proceso:', e);
      setFlow('error');
    }
  }, [handleStepStart, handleStepComplete]);

  // --- Reset a nueva factura ---
  const handleReset = useCallback(() => {
    setFlow('idle');
    setCurrentInvoice(null);
    setFinalResult(null);
    setStepStates({ validator: 'pending', contract: 'pending', guardrail: 'pending', payment: 'pending' });
    setAgentCards({});
    setRunningMessages({});
    setInitialFormData({
      invoice_id: '',
      supplier_id: '',
      supplier_name: '',
      amount: '',
      currency: 'ARS',
      invoice_date: new Date().toISOString().slice(0, 10),
    });
  }, []);

  // --- Orden de las cards en el panel derecho ---
  const stepOrder = ['validator', 'contract', 'guardrail', 'payment'];

  return (
    <div className="ias-root">
      {/* Estilos globales */}
      <style dangerouslySetInnerHTML={{ __html: GLOBAL_CSS }} />

      <Header 
        onShowInvoices={handleShowInvoices}
        onRunGrouper={handleRunGrouper}
      />

      <main className="ias-main">
        {/* Layout principal: form (izq) + panel proceso (der) */}
        <div className="ias-row">
          <aside>
            <InvoiceForm
              onSubmit={handleSubmit}
              disabled={flow === 'processing'}
              initialData={initialFormData}
              onReset={handleReset}
            />
          </aside>

          <section
            className="ias-process-panel"
            aria-live="polite"
            aria-label="Panel de proceso en tiempo real"
          >
            {flow === 'idle' ? (
              <div className="ias-process-empty">
                <Icon name="pulse" size={32} color={COLORS.textMuted} />
                <p style={{ marginTop: 12 }}>Cargá una factura en el formulario para iniciar el flujo de aprobación.</p>
              </div>
            ) : (
              <>
                <div style={{ marginBottom: 18, fontSize: 13, color: COLORS.textMuted }}>
                  {flow === 'processing' && 'Procesando factura — los agentes están trabajando en paralelo.'}
                  {flow === 'completed' && 'Flujo finalizado.'}
                  {flow === 'error' && 'Ocurrió un error en el sistema.'}
                </div>

                <div className="ias-process-grid">
                  {/* Columna izquierda: timeline */}
                  <ProgressLine stepStates={stepStates} />

                  {/* Columna derecha: cards */}
                  <div className="ias-agent-list">
                    {stepOrder.map(name => {
                      const state = stepStates[name];
                      const card = agentCards[name];
                      const titles = {
                        validator: 'Agente validador',
                        contract:  'Control de contrato',
                        guardrail: 'Guardrail',
                        payment:   'Registro de pago',
                      };
                      return (
                        <AgentCard
                          key={name}
                          name={titles[name]}
                          status={state}
                          body={card}
                          runningMessage={runningMessages[name]}
                          footer={card && card.footer}
                        />
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </section>
        </div>

        {/* Resultado final */}
        {flow === 'completed' && finalResult && currentInvoice && (
          <FinalResult
            result={finalResult}
            invoice={currentInvoice}
            onReset={handleReset}
          />
        )}

        {/* Historial */}
        <InvoiceHistory history={history} />
      </main>

      {/* Modal de facturas */}
      <InvoiceModal
        isOpen={showInvoiceModal}
        onClose={() => setShowInvoiceModal(false)}
        invoices={invoices}
        onViewInvoice={handleViewInvoice}
        grouperResult={grouperResult}
        onRunGrouper={handleRunGrouper}
        isRunningGrouper={isRunningGrouper}
      />

      {/* Modal de detalle de factura */}
      <InvoiceDetailModal
        invoice={selectedInvoice}
        onClose={() => setSelectedInvoice(null)}
      />
    </div>
  );
}

export default InvoiceApprovalSystem;

// Bootstrap para uso sin bundler (preview.html). Inofensivo en proyectos con bundler real.
if (typeof window !== 'undefined') window.InvoiceApprovalSystem = InvoiceApprovalSystem;
