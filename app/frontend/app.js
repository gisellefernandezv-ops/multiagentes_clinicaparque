/**
 * InvoiceFlow Back Office — App JavaScript
 *
 * FIX BUG-001: API base sin prefijo '/api' (backend no expone ese prefijo)
 * FIX BUG-002: campos del dashboard mapeados a la respuesta real del backend
 * FIX BUG-003: loadInbox maneja array directo
 * FIX BUG-004: loadHistory maneja array directo
 * FIX BUG-005: chat lee data.message en vez de data.response
 * FIX BUG-007: catch() ahora muestra UI de error real, no mocks
 */

const API = '';  // FIX BUG-001: backend expone /dashboard, /inbox, etc sin prefijo

// ============================================================
// Estado global
// ============================================================
let currentTab = 'dashboard';
let inboxFiles = [];
let chatHistory = [];

// ============================================================
// Utilidades
// ============================================================
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS'
    }).format(amount || 0);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-AR');
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function showError(elId, msg) {
    const el = document.getElementById(elId);
    if (el) el.textContent = '!';
    showToast(msg, 'error');
}

// ============================================================
// Navegación Sidebar
// ============================================================
document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', () => {
        const page = item.dataset.page;

        // Actualizar sidebar
        document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        // Mostrar página
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');
    });
});

// ============================================================
// Inicialización
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadInbox();
    loadHistory();
    checkAgentsHealth();
    loadChatHistory(); // Cargar historial de chat persistente
});

// ============================================================
// Dashboard  (FIX BUG-002)
// ============================================================
async function loadDashboard() {
    const tbody = document.getElementById('recent-tbody');
    tbody.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/dashboard`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        // FIX BUG-002: leer de decisions.{STATUS} y total_amount_approved
        const dec = data.decisions || {};
        document.getElementById('stat-inbox').textContent = data.inbox_count ?? 0;
        document.getElementById('stat-approved').textContent = dec.APPROVED ?? 0;
        document.getElementById('stat-rejected').textContent = dec.REJECTED ?? 0;
        document.getElementById('stat-escalated').textContent = dec.ESCALATED ?? 0;
        document.getElementById('stat-total').textContent = formatCurrency(data.total_amount_approved);

        // FIX BUG-012: usar recent_balanced (3 de cada decision) en lugar de top 10
        renderRecentPayments(data.recent_balanced || data.recent || []);
    } catch (err) {
        // FIX BUG-007: mostrar UI de error real, NO mocks
        console.error('[loadDashboard]', err);
        tbody.innerHTML = `<tr><td colspan="6" class="error">Error: ${err.message}</td></tr>`;
        showError('stat-inbox', 'Error dashboard');
        ['stat-approved', 'stat-rejected', 'stat-escalated', 'stat-total'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '!';
        });
    }
}

function renderRecentPayments(payments) {
    const tbody = document.getElementById('recent-tbody');

    if (!payments.length) {
        tbody.innerHTML = '<tr><td colspan="6">No hay pagos recientes</td></tr>';
        return;
    }

    tbody.innerHTML = payments.map(p => `
        <tr>
            <td>${formatDate(p.registered_at || p.date)}</td>
            <td><strong>${p.invoice_id}</strong></td>
            <td>${p.supplier_id || p.supplier || '-'}</td>
            <td class="amount">${formatCurrency(p.amount)}</td>
            <td><span class="badge ${(p.decision || '').toLowerCase()}">${p.decision || '-'}</span></td>
            <td class="mono">${p.confirmation_id || '-'}</td>
            <td>
                <button class="btn-icon" onclick='openInvoiceModal(${JSON.stringify(p)})' title="Ver detalle">👁️</button>
            </td>
        </tr>
    `).join('');
}

// ============================================================
// Inbox  (FIX BUG-003)
// ============================================================
async function loadInbox() {
    const tbody = document.getElementById('inbox-tbody');
    tbody.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/inbox`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        // FIX BUG-003: backend devuelve array directo, no {files: [...]}
        inboxFiles = Array.isArray(data) ? data : (data.files || []);
        renderInbox();
    } catch (err) {
        // FIX BUG-007: UI de error real
        console.error('[loadInbox]', err);
        tbody.innerHTML = `<tr><td colspan="6" class="error">Error: ${err.message}</td></tr>`;
        inboxFiles = [];
    }
}

function renderInbox() {
    const tbody = document.getElementById('inbox-tbody');

    if (!inboxFiles.length) {
        tbody.innerHTML = '<tr><td colspan="6">No hay facturas en el inbox</td></tr>';
        return;
    }

    // FIX BUG-003: usar invoice_id y supplier_id (no invoice/supplier)
    // FIX BUG-016: incluir fecha de emisión
    tbody.innerHTML = inboxFiles.map(f => {
        const sizeKB = f.size ? (f.size / 1024).toFixed(1) + ' KB' : '-';
        return `
        <tr>
            <td>📄 ${f.filename}</td>
            <td><strong>${f.invoice_id || '-'}</strong></td>
            <td>${f.supplier_id || '-'}</td>
            <td>${f.invoice_date || '-'}</td>
            <td class="amount">${formatCurrency(parseFloat(f.amount) || 0)}</td>
            <td>${sizeKB}</td>
            <td>
                <button class="btn-icon" onclick='openInboxFileModal(${JSON.stringify(f).replace(/'/g, "&apos;")})' title="Ver detalle">👁️</button>
                <button class="btn-small" onclick="processInvoice('${f.filename}')">Procesar</button>
            </td>
        </tr>
    `;
    }).join('');
}

// Upload
const uploadArea = document.getElementById('inbox-upload');
const fileInput = document.getElementById('inbox-file');

if (uploadArea) {
    uploadArea.addEventListener('click', () => fileInput?.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleInboxUpload(e.dataTransfer.files[0]);
        }
    });
}

if (fileInput) {
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleInboxUpload(fileInput.files[0]);
        }
    });
}

async function handleInboxUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch(`${API}/inbox/upload`, {
            method: 'POST',
            body: formData
        });

        if (resp.ok) {
            showToast('Archivo subido exitosamente');
            loadInbox();
        } else {
            showToast(`Error al subir archivo: HTTP ${resp.status}`, 'error');
        }
    } catch (err) {
        console.error('[handleInboxUpload]', err);
        showToast(`Error al subir archivo: ${err.message}`, 'error');
    }
}

async function processInvoice(filename) {
    try {
        const resp = await fetch(`${API}/inbox/process/${filename}`, {
            method: 'POST'
        });

        if (resp.ok) {
            const r = await resp.json();
            showToast(`Factura ${filename} procesada → ${r.decision || '?'}`);
            loadInbox();
            loadDashboard();
        } else {
            showToast(`Error al procesar factura: HTTP ${resp.status}`, 'error');
        }
    } catch (err) {
        console.error('[processInvoice]', err);
        showToast(`Error al procesar factura: ${err.message}`, 'error');
    }
}

document.getElementById('btn-process-all')?.addEventListener('click', async () => {
    try {
        const resp = await fetch(`${API}/inbox/process-all`, { method: 'POST' });
        if (resp.ok) {
            const r = await resp.json();
            showToast(`Procesadas ${r.processed || 0} facturas`);
            loadInbox();
            loadDashboard();
        } else {
            showToast(`Error al procesar todas: HTTP ${resp.status}`, 'error');
        }
    } catch (err) {
        console.error('[btn-process-all]', err);
        showToast(`Error: ${err.message}`, 'error');
    }
});

document.getElementById('btn-refresh')?.addEventListener('click', loadInbox);

document.getElementById('btn-group')?.addEventListener('click', async () => {
    showToast('Agrupando facturas por proveedor...');
    // En producción, esto llamaría al invoice_manager_agent
});

// ============================================================
// Historial  (FIX BUG-004)
// ============================================================
async function loadHistory() {
    const tbody = document.getElementById('history-tbody');
    tbody.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/invoices`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        // FIX BUG-004: backend devuelve array directo
        const list = Array.isArray(data) ? data : (data.invoices || []);
        renderHistory(list);
    } catch (err) {
        console.error('[loadHistory]', err);
        tbody.innerHTML = `<tr><td colspan="8" class="error">Error: ${err.message}</td></tr>`;
    }
}

function renderHistory(invoices) {
    const tbody = document.getElementById('history-tbody');

    if (!invoices.length) {
        tbody.innerHTML = '<tr><td colspan="8">No hay facturas en el historial</td></tr>';
        return;
    }

    tbody.innerHTML = invoices.map(inv => `
        <tr>
            <td>${formatDate(inv.registered_at || inv.invoice_date)}</td>
            <td><strong>${inv.invoice_id}</strong></td>
            <td>${inv.supplier_id || '-'}</td>
            <td class="amount">${formatCurrency(inv.amount)}</td>
            <td><span class="badge ${(inv.decision || '').toLowerCase()}">${inv.decision || '-'}</span></td>
            <td class="mono">${inv.confirmation_id || '-'}</td>
            <td>${inv.payment_status || '-'}</td>
            <td>${inv.rejection_reason || '-'}</td>
            <td>
                <button class="btn-icon" onclick='openInvoiceModal(${JSON.stringify(inv).replace(/'/g, "&apos;")})' title="Ver detalle">👁️</button>
            </td>
        </tr>
    `).join('');
}

document.getElementById('btn-hist-filter')?.addEventListener('click', () => {
    loadHistory();
});

// ============================================================
// Chat interno  (FIX BUG-005 + PERSISTENCIA)
// ============================================================
const internalChatMessages = document.getElementById('internal-chat-messages');
const internalChatInput = document.getElementById('internal-chat-input');
const internalChatSend = document.getElementById('internal-chat-send');

// Session ID persistente (localStorage)
let chatSessionId = localStorage.getItem('chat_session_id') || null;

function loadChatHistory() {
    if (!chatSessionId) return;
    // Cargar mensajes del historial
    fetch(`${API}/chat/sessions/${chatSessionId}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.messages) {
                data.messages.forEach(msg => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        addInternalChatMessage(msg.role, msg.content);
                    }
                });
            }
        })
        .catch(() => {});
}

function saveChatSession(sessionId) {
    chatSessionId = sessionId;
    localStorage.setItem('chat_session_id', sessionId);
}

function addInternalChatMessage(role, text) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${role}`;

    const time = new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

    msg.innerHTML = `
        <div class="chat-meta">${role === 'user' ? 'Operador' : 'IA'} · ${time}</div>
        <div class="chat-text">${text}</div>
    `;

    internalChatMessages.appendChild(msg);
    internalChatMessages.scrollTop = internalChatMessages.scrollHeight;
}

internalChatSend?.addEventListener('click', sendInternalChat);
internalChatInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendInternalChat();
});

async function sendInternalChat() {
    const text = internalChatInput.value.trim();
    if (!text) return;

    addInternalChatMessage('user', text);
    internalChatInput.value = '';

    try {
        const payload = { message: text };
        if (chatSessionId) payload.session_id = chatSessionId;
        
        const resp = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        
        // Guardar session_id para futuras requests
        if (data.session_id && data.session_id !== chatSessionId) {
            saveChatSession(data.session_id);
        }
        
        // FIX BUG-005: leer data.message (no data.response)
        addInternalChatMessage('system', data.message || 'Sin respuesta');
    } catch (err) {
        console.error('[sendInternalChat]', err);
        addInternalChatMessage('system', `Error: ${err.message}`);
    }
}

// ============================================================
// Estado de Agentes (Health Check)
// ============================================================
async function checkAgentsHealth() {
    const statusEl = document.getElementById('agents-status');

    try {
        const resp = await fetch(`${API}/health`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const services = data.microservices || {};
        const downCount = Object.values(services).filter(s => s.status === 'down').length;

        if (downCount > 0) {
            statusEl.innerHTML = `
                <span class="agents-indicator error">🔴</span>
                <span class="agents-text">${downCount} servicio(s) caído(s)</span>
            `;
        } else {
            statusEl.innerHTML = `
                <span class="agents-indicator ok">🟢</span>
                <span class="agents-text">Todos los servicios OK</span>
            `;
        }
    } catch (err) {
        console.error('[checkAgentsHealth]', err);
        statusEl.innerHTML = `
            <span class="agents-indicator error">🔴</span>
            <span class="agents-text">No se pudo verificar: ${err.message}</span>
        `;
    }
}

// Refrescar health cada 30 segundos
setInterval(checkAgentsHealth, 30000);

// Auto-refresh inbox y dashboard cada 10 segundos (BUG-022)
setInterval(() => {
    // Solo refresh si la página de inbox está visible
    const inboxPage = document.getElementById('page-inbox');
    if (inboxPage && inboxPage.classList.contains('active')) {
        loadInbox();
    }
    // Refresh dashboard siempre
    loadDashboard();
}, 10000);

// ============================================================
// Evaluación
// ============================================================
async function loadEvaluation() {
    const tbody = document.getElementById('eval-tbody');
    tbody.innerHTML = '<tr><td colspan="5">Cargando…</td></tr>';

    // FIX BUG-006: backend ahora monta /tests/eval/datasets
    try {
        const resp = await fetch('/tests/eval/datasets/invoiceflow-dataset.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        renderEvaluation(data.test_cases || []);
    } catch (err) {
        console.error('[loadEvaluation]', err);
        tbody.innerHTML = `<tr><td colspan="5" class="error">Error: ${err.message}</td></tr>`;
    }
}

function renderEvaluation(testCases) {
    const tbody = document.getElementById('eval-tbody');

    if (!testCases.length) {
        tbody.innerHTML = '<tr><td colspan="5">No hay casos en el dataset</td></tr>';
        return;
    }

    tbody.innerHTML = testCases.slice(0, 20).map(tc => {
        const passed = tc.expected?.passed !== false;
        return `
            <tr>
                <td><strong>${tc.id}</strong></td>
                <td><span class="badge ${tc.category === 'happy_path' ? 'approved' : 'pending'}">${tc.category}</span></td>
                <td>${tc.description}</td>
                <td><span class="badge ${passed ? 'approved' : 'rejected'}">${passed ? '✅ Pasó' : '❌ Falló'}</span></td>
                <td>${((tc.expected?.score || 1.0) * 100).toFixed(0)}%</td>
            </tr>
        `;
    }).join('');
}

// Cargar cuando se muestra la página de evaluación
const evalPage = document.getElementById('page-evaluacion');
if (evalPage) {
    const observer = new MutationObserver(() => {
        if (evalPage.classList.contains('active')) {
            loadEvaluation();
            observer.disconnect();
        }
    });
    observer.observe(evalPage, { attributes: true, attributeFilter: ['class'] });
}

// FIX BUG-019: Chat - "Asistente IA" con mensaje de bienvenida
let chatWelcomeShown = false;
const chatPage = document.getElementById('page-chat');
if (chatPage) {
    const observer = new MutationObserver(() => {
        if (chatPage.classList.contains('active')) {
            if (!chatWelcomeShown) {
                addInternalChatMessage('system',
                    '👋 ¡Hola! Soy tu **Asistente Inteligente GI**. ' +
                    'Estoy acá para ayudarte con el sistema InvoiceFlow.\n\n' +
                    '💡 **Probalo con:**\n' +
                    '• "me podras decir los montos" → te muestro los montos del inbox\n' +
                    '• "qué facturas hay en el inbox?" → lista las pendientes\n' +
                    '• "mostrame el historial" → pagos registrados\n' +
                    '• "cuánto suman las facturas" → totales por estado\n' +
                    '• "resumen" → overview del sistema\n' +
                    '• "procesá todo el inbox" → procesa las pendientes\n\n' +
                    '¿En qué te puedo ayudar?'
                );
                chatWelcomeShown = true;
            }
        }
    });
    observer.observe(chatPage, { attributes: true, attributeFilter: ['class'] });
}

// ============================================================
// FIX BUG-016: ABM de Proveedores
// ============================================================
let suppliersCache = [];
let contractsCache = {};

async function loadSuppliers() {
    const tbody = document.getElementById('suppliers-tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;">Cargando…</td></tr>';

    try {
        // Cargar suppliers y contracts en paralelo via proxy same-origin
        const [supResp, contResp] = await Promise.all([
            fetch(`${API}/suppliers/proxy-list`).then(r => r.json()),
            fetch(`${API}/suppliers/proxy-contracts`).then(r => r.json()),
        ]);
        suppliersCache = supResp || [];
        contractsCache = {};
        (contResp || []).forEach(c => { contractsCache[c.supplier_id] = c; });
        renderSuppliers();
    } catch (err) {
        console.error('[loadSuppliers]', err);
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center;color:#c00;">Error: ${err.message}</td></tr>`;
    }
}

function renderSuppliers() {
    const tbody = document.getElementById('suppliers-tbody');
    const search = (document.getElementById('supplier-search')?.value || '').toLowerCase();
    let list = suppliersCache;
    if (search) {
        list = list.filter(s =>
            (s.name || '').toLowerCase().includes(search) ||
            (s.cuit || '').toLowerCase().includes(search) ||
            (s.supplier_id || '').toLowerCase().includes(search)
        );
    }
    if (!list.length) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;">Sin proveedores</td></tr>';
        return;
    }
    tbody.innerHTML = list.map(s => {
        const c = contractsCache[s.supplier_id];
        const mode = c ? c.mode : '-';
        const limit = c ? `${c.contract_limit.toLocaleString('es-AR')}` : '-';
        const statusBadge = s.status === 'ACTIVE'
            ? '<span class="badge approved">✅ Activo</span>'
            : s.status === 'INACTIVE'
            ? '<span class="badge rejected">❌ Inactivo</span>'
            : '<span class="badge escalated">⏸️ Suspendido</span>';
        return `
            <tr>
                <td><strong>${s.supplier_id}</strong></td>
                <td>${s.name}</td>
                <td class="mono">${s.cuit}</td>
                <td>${s.category || '-'}</td>
                <td>${s.email || '-'}</td>
                <td>${s.phone || '-'}</td>
                <td>${c ? '✅' : '❌'}</td>
                <td>${mode === 'EXACTO' ? '🎯 Exacto' : mode === 'NO_SUPERAR' ? '≤ No superar' : mode}</td>
                <td class="mono">${limit}</td>
                <td>${statusBadge}</td>
                <td style="white-space: nowrap;">
                    <button class="btn-icon" onclick='editSupplier(${JSON.stringify(s).replace(/'/g, "&apos;")})' title="Editar proveedor" style="font-size:18px; padding:6px 10px;">✏️</button>
                    <button class="btn-icon" onclick="toggleSupplierStatus('${s.supplier_id}', '${s.status}')" title="${s.status === 'ACTIVE' ? 'Desactivar' : 'Activar'}" style="font-size:18px; padding:6px 10px;">
                        ${s.status === 'ACTIVE' ? '🔒' : '🔓'}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

document.getElementById('supplier-search')?.addEventListener('input', renderSuppliers);
document.getElementById('btn-refresh-suppliers')?.addEventListener('click', loadSuppliers);
document.getElementById('btn-new-supplier')?.addEventListener('click', () => openSupplierForm());

function toggleSupplierStatus(sid, currentStatus) {
    const newStatus = currentStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    fetch(`${API}/suppliers/proxy-update/${sid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
    })
    .then(r => r.json())
    .then(() => {
        showToast(`Proveedor ${sid} → ${newStatus}`);
        loadSuppliers();
    })
    .catch(err => showToast(`Error: ${err.message}`, 'error'));
}

function editSupplier(s) {
    openSupplierForm(s);
}

function openSupplierForm(supplier = null) {
    const isEdit = !!supplier;
    const c = supplier ? contractsCache[supplier.supplier_id] : null;
    const html = `
        <div id="invoice-modal" class="modal-overlay" onclick="closeModal(event)">
            <div class="modal-content modal-wide" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>${isEdit ? '✏️ Editar' : '➕ Nuevo'} Proveedor</h2>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <form id="supplier-form" onsubmit="return submitSupplierForm(event, ${isEdit ? `'${supplier.supplier_id}'` : 'null'})">
                        <div class="form-section">
                            <h3>📋 Datos del Proveedor</h3>
                            <div class="form-grid">
                                <div class="form-field">
                                    <label>ID (opcional, se autogenera)</label>
                                    <input type="text" id="f-supplier_id" value="${supplier?.supplier_id || ''}" placeholder="SUP006" pattern="SUP\\d{3,}">
                                </div>
                                <div class="form-field">
                                    <label>Razón Social *</label>
                                    <input type="text" id="f-name" value="${supplier?.name || ''}" required>
                                </div>
                                <div class="form-field">
                                    <label>CUIT *</label>
                                    <input type="text" id="f-cuit" value="${supplier?.cuit || ''}" required pattern="\\d{2}-?\\d{8}-?\\d" placeholder="30-12345678-9">
                                </div>
                                <div class="form-field">
                                    <label>Estado</label>
                                    <select id="f-status">
                                        <option value="ACTIVE" ${supplier?.status === 'ACTIVE' || !supplier ? 'selected' : ''}>✅ Activo</option>
                                        <option value="INACTIVE" ${supplier?.status === 'INACTIVE' ? 'selected' : ''}>❌ Inactivo</option>
                                        <option value="SUSPENDED" ${supplier?.status === 'SUSPENDED' ? 'selected' : ''}>⏸️ Suspendido</option>
                                    </select>
                                </div>
                                <div class="form-field">
                                    <label>Categoría</label>
                                    <input type="text" id="f-category" value="${supplier?.category || ''}" placeholder="Servicios IT">
                                </div>
                                <div class="form-field">
                                    <label>Email</label>
                                    <input type="email" id="f-email" value="${supplier?.email || ''}">
                                </div>
                                <div class="form-field">
                                    <label>Teléfono</label>
                                    <input type="tel" id="f-phone" value="${supplier?.phone || ''}">
                                </div>
                            </div>
                        </div>

                        <div class="form-section">
                            <h3>📋 Contrato (opcional)</h3>
                            <p style="color:#64748b;font-size:13px;margin:8px 0 16px;">
                                Definí el modo de validación del contrato. Se usa para validar cada factura.
                            </p>
                            <div class="form-field">
                                <label>Modo de validación</label>
                                <div class="radio-group">
                                    <label class="radio-option">
                                        <input type="radio" name="mode" value="NO_SUPERAR" ${(!c || c.mode === 'NO_SUPERAR') ? 'checked' : ''}>
                                        <span><strong>No superar monto</strong> — La factura puede ser menor o igual al límite (default)</span>
                                    </label>
                                    <label class="radio-option">
                                        <input type="radio" name="mode" value="EXACTO" ${c?.mode === 'EXACTO' ? 'checked' : ''}>
                                        <span><strong>Monto exacto</strong> — La factura debe ser EXACTAMENTE igual al límite</span>
                                    </label>
                                </div>
                            </div>
                            <div class="form-grid">
                                <div class="form-field">
                                    <label>Monto límite (contrato)</label>
                                    <input type="number" id="f-contract_limit" value="${c?.contract_limit || ''}" min="0" step="0.01" placeholder="150000">
                                </div>
                                <div class="form-field">
                                    <label>Fecha inicio</label>
                                    <input type="date" id="f-start_date" value="${c?.start_date || ''}">
                                </div>
                                <div class="form-field">
                                    <label>Fecha vencimiento</label>
                                    <input type="date" id="f-end_date" value="${c?.end_date || ''}">
                                </div>
                                <div class="form-field">
                                    <label>Archivo contrato (opcional)</label>
                                    <input type="file" id="f-contract_file" accept=".txt,.pdf">
                                </div>
                            </div>
                        </div>

                        <div class="form-actions">
                            <button type="button" class="btn-secondary" onclick="closeModal()">Cancelar</button>
                            <button type="submit" class="btn-primary">${isEdit ? 'Guardar cambios' : 'Crear proveedor'}</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    closeModal();
    document.body.insertAdjacentHTML('beforeend', html);
}

function submitSupplierForm(event, editId) {
    event.preventDefault();
    const data = {
        supplier_id: document.getElementById('f-supplier_id').value || null,
        name: document.getElementById('f-name').value,
        cuit: document.getElementById('f-cuit').value,
        status: document.getElementById('f-status').value,
        category: document.getElementById('f-category').value || null,
        email: document.getElementById('f-email').value || null,
        phone: document.getElementById('f-phone').value || null,
    };
    const limit = parseFloat(document.getElementById('f-contract_limit').value);
    if (limit && limit > 0) {
        data.contract = {
            contract_limit: limit,
            mode: document.querySelector('input[name="mode"]:checked').value,
            start_date: document.getElementById('f-start_date').value || null,
            end_date: document.getElementById('f-end_date').value || null,
            file_name: document.getElementById('f-contract_file')?.files[0]?.name || null,
        };
    }

    const url = editId
        ? `${API}/suppliers/proxy-update/${editId}`
        : `${API}/suppliers/proxy-create`;
    const method = editId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e)))
    .then(() => {
        showToast(editId ? 'Proveedor actualizado' : 'Proveedor creado');
        closeModal();
        loadSuppliers();
    })
    .catch(err => showToast(`Error: ${err.detail?.[0]?.msg || err.message || JSON.stringify(err)}`, 'error'));
}

// Cargar cuando se muestra la pagina de proveedores
const suppliersPage = document.getElementById('page-proveedores');
if (suppliersPage) {
    const observer = new MutationObserver(() => {
        if (suppliersPage.classList.contains('active')) {
            loadSuppliers();
            observer.disconnect();
        }
    });
    observer.observe(suppliersPage, { attributes: true, attributeFilter: ['class'] });
}

// ============================================================
// Estado de Agentes  (FIX BUG-010)
// ============================================================

// Tracking de última respuesta OK por servicio (para calcular "Hace X min")
const agentLastSeen = {};

async function pingService(name, url) {
    try {
        const resp = await fetch(url, { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return { name, status: data.status || 'unknown', error: null };
    } catch (err) {
        return { name, status: 'down', error: err.message };
    }
}

async function loadAgentsStatus() {
    const grid = document.getElementById('agents-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="agent-card" style="grid-column: 1 / -1; text-align: center; padding: 32px;"><span style="color: #888;">Verificando servicios…</span></div>';

    // FIX BUG-011: usar proxy same-origin del backend en vez de fetch cross-origin
    // (los microservicios 8001/8002/8003 no tienen CORS)
    let data;
    try {
        const resp = await fetch(`${API}/agents/health`, { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        data = await resp.json();
    } catch (err) {
        console.error('[loadAgentsStatus]', err);
        grid.innerHTML = `<div class="agent-card" style="grid-column: 1 / -1; text-align: center; padding: 32px;"><span style="color: #c00;">Error: ${err.message}</span></div>`;
        return;
    }

    // Config visual por servicio
    const servicesConfig = {
        'invoiceflow-backend': { icon: '🧠', port: 8000 },
        'supplier-service':    { icon: '📦', port: 8001 },
        'contract-service':    { icon: '📋', port: 8002 },
        'external-auditor':    { icon: '🔍', port: 8003 },
    };

    const now = Date.now();

    // Función para renderizar un servicio
    function renderService(name, info, cfg) {
        const isOnline = info.ok;
        if (isOnline) agentLastSeen[name] = now;

        let lastSeen = '—';
        if (agentLastSeen[name]) {
            const diffSec = Math.floor((now - agentLastSeen[name]) / 1000);
            if (diffSec < 60) lastSeen = `Hace ${diffSec} seg`;
            else if (diffSec < 3600) lastSeen = `Hace ${Math.floor(diffSec / 60)} min`;
            else lastSeen = `Hace ${Math.floor(diffSec / 3600)} h`;
        } else if (isOnline) {
            lastSeen = 'Ahora';
        }

        return `
            <div class="agent-card ${isOnline ? '' : 'warning'}">
                <div class="agent-header">
                    <span class="agent-icon">${cfg.icon}</span>
                    <span class="agent-name">${cfg.description || name}</span>
                    <span class="agent-status ${isOnline ? 'online' : 'offline'}">
                        ${isOnline ? '🟢 Online' : '🔴 Caído'}
                    </span>
                </div>
                <div class="agent-stats">
                    <div class="agent-stat">
                        <span class="stat-label">Servicio</span>
                        <span class="stat-value">${name}</span>
                    </div>
                    <div class="agent-stat">
                        <span class="stat-label">Puerto</span>
                        <span class="stat-value">${cfg.port}</span>
                    </div>
                    <div class="agent-stat">
                        <span class="stat-label">Última verificación</span>
                        <span class="stat-value">${lastSeen}</span>
                    </div>
                </div>
                ${info.error ? `<div style="color:#c00;font-size:12px;margin-top:8px;">Error: ${info.error}</div>` : ''}
            </div>
        `;
    }

    // Renderizar secciones
    const criticalServices = data.critical_services || {};
    const secondaryServices = data.secondary_services || {};

    let html = '';

    // Sección de estado general
    const criticalOk = Object.values(criticalServices).every(s => s.ok);
    html += `
        <div class="status-summary ${criticalOk ? 'ok' : 'warning'}">
            <span class="status-icon">${criticalOk ? '✅' : '⚠️'}</span>
            <span class="status-text">
                <strong>${criticalOk ? 'Todos los servicios críticos operativos' : 'Servicios críticos con problemas'}</strong><br>
                <small>Estado general: ${data.status || 'desconocido'}</small>
            </span>
        </div>
    `;

    // Servicios críticos
    html += '<h3 class="section-title" style="margin-top:20px;">🔴 SERVICIOS CRÍTICOS</h3>';
    html += '<p style="color:#64748b;font-size:13px;margin-bottom:16px;">Estos servicios son necesarios para el funcionamiento del sistema.</p>';
    html += '<div class="agents-grid">';
    for (const [name, info] of Object.entries(criticalServices)) {
        html += renderService(name, info, servicesConfig[name] || { icon: '❓', port: '?', description: name });
    }
    html += '</div>';

    // Servicios secundarios
    html += '<h3 class="section-title" style="margin-top:32px;">🟡 SERVICIOS SECUNDARIOS</h3>';
    html += '<p style="color:#64748b;font-size:13px;margin-bottom:16px;">Servicios opcionales para funcionalidad extendida.</p>';
    html += '<div class="agents-grid">';
    for (const [name, info] of Object.entries(secondaryServices)) {
        html += renderService(name, info, servicesConfig[name] || { icon: '❓', port: '?', description: name });
    }
    html += '</div>';

    grid.innerHTML = html;
}

// Auto-refresh cada 15 segundos
setInterval(loadAgentsStatus, 15000);

// Cargar cuando se muestra la página de Observabilidad
const agentsPage = document.getElementById('page-observabilidad');
if (agentsPage) {
    const observer = new MutationObserver(() => {
        if (agentsPage.classList.contains('active')) {
            loadAgentsStatus();
            observer.disconnect();
        }
    });
    observer.observe(agentsPage, { attributes: true, attributeFilter: ['class'] });
}

// ============================================================
// Modal de detalle (FIX BUG-012)
// ============================================================
function openInvoiceModal(invoice) {
    // FIX BUG-015: modal con 2 subsecciones claras:
    //   1) 📄 FACTURA ORIGINAL (lo que vino)
    //   2) 🔍 DECISIÓN DEL SISTEMA (qué decidió y por qué)
    const secOriginal = [];
    const secDecision = [];

    // ========== SECCIÓN 1: FACTURA ORIGINAL ==========
    // Identificación
    const idFields = [
        ['Tipo de comprobante', invoice.tipo_comprobante || 'FACTURA'],
        ['Código AFIP',        invoice.codigo_tipo],
        ['Punto de venta',      invoice.punto_venta],
        ['Número comprobante',  invoice.numero_comprobante],
        ['ID interno',          invoice.invoice_id],
        ['Fecha emisión',       invoice.invoice_date],
    ];
    secOriginal.push({ titulo: 'Identificación del Comprobante', fields: idFields });

    // Emisor
    if (invoice.emisor_razon_social || invoice.emisor_cuit) {
        secOriginal.push({
            titulo: '🏢 Emisor',
            fields: [
                ['Razón Social',   invoice.emisor_razon_social || invoice.supplier_name],
                ['CUIT',           invoice.emisor_cuit || invoice.cuit],
                ['Condición IVA',  invoice.emisor_condicion_iva],
                ['Domicilio',      invoice.emisor_direccion],
                ['Rubro',          invoice.emisor_rubro],
                ['Ing. Brutos',    invoice.emisor_ingresos_brutos],
                ['Inicio Act.',    invoice.emisor_inicio_actividades],
            ],
        });
    }

    // Receptor
    if (invoice.receptor_razon_social || invoice.receptor_cuit) {
        secOriginal.push({
            titulo: '👤 Receptor',
            fields: [
                ['Señor/es',       invoice.receptor_razon_social],
                ['CUIT',           invoice.receptor_cuit],
                ['Domicilio',      invoice.receptor_direccion],
                ['Localidad',      invoice.receptor_localidad],
                ['Condición IVA',  invoice.receptor_condicion_iva],
            ],
        });
    }

    // Condiciones comerciales
    secOriginal.push({
        titulo: '💳 Condiciones Comerciales',
        fields: [
            ['Condición de venta', invoice.condicion_venta],
            ['Remito Nº',          invoice.remito_numero],
        ],
    });

    // Tabla de items
    let itemsHtml = '';
    if (invoice.items && invoice.items.length > 0) {
        const letra = invoice.letra_comprobante || '?';
        const colLabel = (letra === 'A') ? 'P. Unit. (s/IVA)' : 'P. Unitario';
        const importeLabel = (letra === 'A') ? 'Importe (s/IVA)' : 'Importe';
        itemsHtml = `
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Cant.</th>
                        <th>Descripción</th>
                        <th style="text-align: right;">${colLabel}</th>
                        <th style="text-align: right;">${importeLabel}</th>
                    </tr>
                </thead>
                <tbody>
                    ${invoice.items.map(it => `
                        <tr>
                            <td>${it.cantidad}</td>
                            <td>${it.descripcion}</td>
                            <td style="text-align: right;">${formatCurrency(it.precio_unitario)}</td>
                            <td style="text-align: right;">${formatCurrency(it.importe)}</td>
                        </tr>
                    `).join('')}
                </tbody>
                <tfoot>
                    ${letra === 'A' ? `
                        <tr>
                            <td colspan="3" style="text-align: right;"><strong>Subtotal gravado</strong></td>
                            <td style="text-align: right;"><strong>${formatCurrency(invoice.subtotal_gravado || 0)}</strong></td>
                        </tr>
                        <tr>
                            <td colspan="3" style="text-align: right;"><strong>IVA 21%</strong></td>
                            <td style="text-align: right;"><strong>${formatCurrency(invoice.iva_21 || 0)}</strong></td>
                        </tr>
                    ` : ''}
                    <tr class="total-row">
                        <td colspan="3" style="text-align: right;"><strong>TOTAL</strong></td>
                        <td style="text-align: right;"><strong>${formatCurrency(invoice.amount)}</strong></td>
                    </tr>
                </tfoot>
            </table>
        `;
    }

    // Datos fiscales
    if (invoice.cae || invoice.codigo_barras) {
        secOriginal.push({
            titulo: '🛡️ Datos Fiscales',
            fields: [
                ['CAE',              invoice.cae],
                ['Vencimiento CAE',  invoice.cae_vencimiento],
                ['Código de barras', invoice.codigo_barras],
            ],
        });
    }

    // Impresor
    if (invoice.impresor_razon_social) {
        secOriginal.push({
            titulo: '🖨️ Impresor del Comprobante',
            fields: [
                ['Razón Social',   invoice.impresor_razon_social],
                ['CUIT',           invoice.impresor_cuit],
                ['Expediente',     invoice.impresor_expediente],
                ['Fecha Imp.',     invoice.impresor_fecha],
                ['Rango',          `${invoice.impresor_rango_desde} al ${invoice.impresor_rango_hasta}`],
            ],
        });
    }

    // ========== SECCIÓN 2: DECISIÓN DEL SISTEMA ==========
    const decisionFields = [
        ['Decisión final',   decisionLabel(invoice.decision)],
        ['Estado de pago',   invoice.payment_status],
        ['Confirmation ID',  invoice.confirmation_id],
        ['Fecha de registro', formatDate(invoice.registered_at)],
        ['Moneda',           invoice.currency || 'ARS'],
        ['Proveedor (mapeo)', invoice.supplier_id],
    ];
    secDecision.push({ titulo: 'Decisión y Trazabilidad', fields: decisionFields });

    // Razón de rechazo / regla aplicada
    if (invoice.rejection_reason || invoice.guardrail_reason) {
        secDecision.push({
            titulo: '⚠️ Motivo de Decisión',
            fields: [
                ['Razón de rechazo', invoice.rejection_reason],
                ['Regla aplicada',   invoice.guardrail_reason],
                ['Acción guardrail', invoice.guardrail_action],
            ],
        });
    }

    // Steps del flujo
    if (invoice.steps && invoice.steps.length > 0) {
        let stepsHtml = `
            <ol class="steps-list">
                ${invoice.steps.map(s => `
                    <li>
                        <strong>${s.step || s.name || 'step'}:</strong>
                        ${s.passed !== undefined ? (s.passed ? '✅' : '❌') : ''}
                        ${s.action ? `[${s.action}]` : ''}
                        ${s.reason ? `<br><em>${s.reason}</em>` : ''}
                    </li>
                `).join('')}
            </ol>
        `;
        secDecision.push({
            titulo: '🔄 Flujo de Validación Ejecutado',
            html: stepsHtml,
        });
    }

    // Auditoría A2A
    if (invoice.audit) {
        let auditHtml = `
            <table class="detail-table">
                <tr><td><strong>Audit ID</strong></td><td>${invoice.audit.audit_id}</td></tr>
                <tr><td><strong>Resultado</strong></td><td>${invoice.audit.audit_result}</td></tr>
                <tr><td><strong>Confianza</strong></td><td>${invoice.audit.confidence}</td></tr>
                <tr><td><strong>Resumen</strong></td><td>${invoice.audit.summary || '-'}</td></tr>
            </table>
            ${invoice.audit.findings ? `
                <h4 style="margin-top:12px;">Hallazgos:</h4>
                <ul class="audit-findings">
                    ${invoice.audit.findings.map(f =>
                        `<li><strong>${f.category}</strong> [${f.severity}]: ${f.description}
                         <br><em>→ ${f.recommendation}</em></li>`
                    ).join('')}
                </ul>
            ` : ''}
        `;
        secDecision.push({
            titulo: '🔍 Auditoría Externa (A2A)',
            html: auditHtml,
        });
    }

    // Origen del archivo
    if (invoice.source_file) {
        secDecision.push({
            titulo: '📁 Origen',
            fields: [
                ['Archivo fuente', invoice.source_file],
            ],
        });
    }

    const renderSection = (s) => {
        if (s.html) return `<div class="section-block">${s.titulo ? `<h3>${s.titulo}</h3>` : ''}${s.html}</div>`;
        const fields = (s.fields || []).filter(([_, v]) => v != null && v !== '');
        if (fields.length === 0) return '';
        return `
            <div class="section-block">
                ${s.titulo ? `<h3>${s.titulo}</h3>` : ''}
                <table class="detail-table">
                    ${fields.map(([k, v]) => `
                        <tr>
                            <td><strong>${k}</strong></td>
                            <td>${v}</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        `;
    };

    const html = `
        <div id="invoice-modal" class="modal-overlay" onclick="closeModal(event)">
            <div class="modal-content modal-wide" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>📄 ${invoice.tipo_comprobante || 'Factura'} ${invoice.invoice_id || ''}</h2>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="modal-section-header section-original">
                        📄 FACTURA ORIGINAL <small>(datos del comprobante recibido)</small>
                    </div>
                    ${secOriginal.map(renderSection).join('')}
                    ${itemsHtml ? `
                        <div class="section-block">
                            <h3>📦 Items (${invoice.items.length})</h3>
                            ${itemsHtml}
                        </div>
                    ` : ''}
                    <div class="modal-section-header section-decision">
                        🔍 DECISIÓN DEL SISTEMA <small>(qué decidió hacer InvoiceFlow y por qué)</small>
                    </div>
                    ${secDecision.map(renderSection).join('')}
                </div>
            </div>
        </div>
    `;
    closeModal();
    document.body.insertAdjacentHTML('beforeend', html);
}

function decisionLabel(decision) {
    const map = {
        'APPROVED': '✅ APROBADA',
        'REJECTED': '❌ RECHAZADA',
        'ESCALATED': '⏫ ESCALADA',
        'PENDING': '⏳ PENDIENTE',
    };
    return map[decision] || (decision || '-');
}

function openInboxFileModal(file) {
    // FIX BUG-014: si el parser devuelve items y demas campos, los mostramos
    const html = `
        <div id="invoice-modal" class="modal-overlay" onclick="closeModal(event)">
            <div class="modal-content modal-wide" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>📄 ${file.tipo_comprobante || 'Factura'} - ${file.filename}</h2>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="section-block">
                        <h3>📋 Identificación</h3>
                        <table class="detail-table">
                            <tr><td><strong>Archivo</strong></td><td>${file.filename}</td></tr>
                            <tr><td><strong>Tamaño</strong></td><td>${file.size ? (file.size/1024).toFixed(1) + ' KB' : '-'}</td></tr>
                            <tr><td><strong>ID Factura</strong></td><td>${file.invoice_id || '—'}</td></tr>
                            <tr><td><strong>Punto de venta</strong></td><td>${file.punto_venta || '—'}</td></tr>
                            <tr><td><strong>Número comprobante</strong></td><td>${file.numero_comprobante || '—'}</td></tr>
                            <tr><td><strong>Fecha emisión</strong></td><td>${file.invoice_date || '—'}</td></tr>
                            <tr><td><strong>Proveedor</strong></td><td>${file.supplier_id || '—'}</td></tr>
                            <tr><td><strong>CUIT</strong></td><td>${file.emisor_cuit || file.cuit || '—'}</td></tr>
                            <tr><td><strong>Total</strong></td><td>${file.amount ? formatCurrency(parseFloat(file.amount)) : '—'}</td></tr>
                        </table>
                    </div>
                    ${file.items && file.items.length > 0 ? `
                        <div class="section-block">
                            <h3>📦 Items (${file.items.length})</h3>
                            <table class="items-table">
                                <thead>
                                    <tr>
                                        <th>Cant.</th>
                                        <th>Descripción</th>
                                        <th style="text-align: right;">P. Unitario</th>
                                        <th style="text-align: right;">Importe</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${file.items.map(it => `
                                        <tr>
                                            <td>${it.cantidad}</td>
                                            <td>${it.descripcion}</td>
                                            <td style="text-align: right;">${formatCurrency(it.precio_unitario)}</td>
                                            <td style="text-align: right;">${formatCurrency(it.importe)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                                <tfoot>
                                    <tr>
                                        <td colspan="3" style="text-align: right;"><strong>TOTAL</strong></td>
                                        <td style="text-align: right;"><strong>${formatCurrency(file.amount)}</strong></td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                    ` : ''}
                    <p style="margin-top: 16px;">
                        <em>Hacé click en <strong>Procesar</strong> para validar y registrar esta factura.</em>
                    </p>
                </div>
            </div>
        </div>
    `;
    closeModal();
    document.body.insertAdjacentHTML('beforeend', html);
}

function closeModal(event) {
    if (event && event.target && !event.target.classList.contains('modal-overlay')) return;
    const modal = document.getElementById('invoice-modal');
    if (modal) modal.remove();
}

// Cerrar modal con tecla ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});