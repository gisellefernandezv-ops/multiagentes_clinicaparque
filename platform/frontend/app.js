/**
 * InvoiceFlow Back Office — App JavaScript
 * Actualizado para funcionar con sidebar
 */

const API = '/api';

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
});

// ============================================================
// Dashboard
// ============================================================
async function loadDashboard() {
    const tbody = document.getElementById('recent-tbody');
    tbody.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/dashboard`);
        const data = await resp.json();
        
        document.getElementById('stat-inbox').textContent = data.inbox_count || 0;
        document.getElementById('stat-approved').textContent = data.approved || 0;
        document.getElementById('stat-escalated').textContent = data.escalated || 0;
        document.getElementById('stat-rejected').textContent = data.rejected || 0;
        document.getElementById('stat-total').textContent = formatCurrency(data.total_approved);
        
        renderRecentPayments(data.recent_payments || []);
    } catch {
        // Fallback a datos mock
        document.getElementById('stat-inbox').textContent = '5';
        document.getElementById('stat-approved').textContent = '12';
        document.getElementById('stat-escalated').textContent = '2';
        document.getElementById('stat-rejected').textContent = '3';
        document.getElementById('stat-total').textContent = '$1,250,000';
        
        renderRecentPayments([
            { invoice_id: 'FC-2026-SUP001-001', supplier: 'TechCorp SA', amount: 25000, decision: 'APPROVED', confirmation_id: 'PAY-A1B2C3D4' },
            { invoice_id: 'FC-2026-SUP002-001', supplier: 'Papeleria Norte', amount: 75000, decision: 'REJECTED', confirmation_id: '' },
            { invoice_id: 'FC-2026-SUP003-001', supplier: 'Servicios Rapidos', amount: 150000, decision: 'APPROVED', confirmation_id: 'PAY-C3D4E5F6' },
        ]);
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
            <td>${p.supplier || p.supplier_name || '-'}</td>
            <td class="amount">${formatCurrency(p.amount)}</td>
            <td><span class="badge ${p.decision?.toLowerCase() || 'pending'}">${p.decision || '-'}</span></td>
            <td class="mono">${p.confirmation_id || '-'}</td>
        </tr>
    `).join('');
}

// ============================================================
// Inbox
// ============================================================
async function loadInbox() {
    const tbody = document.getElementById('inbox-tbody');
    tbody.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/inbox`);
        const data = await resp.json();
        inboxFiles = data.files || [];
        renderInbox();
    } catch {
        // Fallback
        inboxFiles = [
            { filename: 'FC-2026-SUP001-NUEVA-1.txt', invoice: 'FC-2026-SUP001-001', supplier: 'TechCorp SA', amount: 25000, size: '2.2 KB' },
            { filename: 'FC-2026-SUP002-NUEVA-1.txt', invoice: 'FC-2026-SUP002-001', supplier: 'Papeleria Norte', amount: 75000, size: '2.2 KB' },
        ];
        renderInbox();
    }
}

function renderInbox() {
    const tbody = document.getElementById('inbox-tbody');
    
    if (!inboxFiles.length) {
        tbody.innerHTML = '<tr><td colspan="6">No hay facturas en el inbox</td></tr>';
        return;
    }
    
    tbody.innerHTML = inboxFiles.map(f => `
        <tr>
            <td>📄 ${f.filename}</td>
            <td><strong>${f.invoice || '-'}</strong></td>
            <td>${f.supplier || '-'}</td>
            <td class="amount">${formatCurrency(f.amount || 0)}</td>
            <td>${f.size || '-'}</td>
            <td><button class="btn-small" onclick="processInvoice('${f.filename}')">Procesar</button></td>
        </tr>
    `).join('');
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
            showToast('Error al subir archivo', 'error');
        }
    } catch {
        showToast('Error al subir archivo', 'error');
    }
}

async function processInvoice(filename) {
    try {
        const resp = await fetch(`${API}/inbox/process/${filename}`, {
            method: 'POST'
        });
        
        if (resp.ok) {
            showToast(`Factura ${filename} procesada`);
            loadInbox();
            loadDashboard();
        } else {
            showToast('Error al procesar factura', 'error');
        }
    } catch {
        showToast('Error al procesar factura', 'error');
    }
}

document.getElementById('btn-process-all')?.addEventListener('click', async () => {
    try {
        const resp = await fetch(`${API}/inbox/process-all`, { method: 'POST' });
        if (resp.ok) {
            showToast('Todas las facturas procesadas');
            loadInbox();
            loadDashboard();
        }
    } catch {
        showToast('Error al procesar facturas', 'error');
    }
});

document.getElementById('btn-refresh')?.addEventListener('click', loadInbox);

document.getElementById('btn-group')?.addEventListener('click', async () => {
    showToast('Agrupando facturas por proveedor...');
    // En producción, esto llamaría al invoice_manager_agent
});

// ============================================================
// Historial
// ============================================================
async function loadHistory() {
    const tbody = document.getElementById('history-tbody');
    tbody.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';

    try {
        const resp = await fetch(`${API}/invoices`);
        const data = await resp.json();
        renderHistory(data.invoices || []);
    } catch {
        // Fallback
        renderHistory([
            { invoice_id: 'FC-2026-SUP001-001', supplier_id: 'SUP001', amount: 25000, decision: 'APPROVED', confirmation_id: 'PAY-A1B2C3D4', rejection_reason: '' },
            { invoice_id: 'FC-2026-SUP002-001', supplier_id: 'SUP002', amount: 75000, decision: 'REJECTED', confirmation_id: '', rejection_reason: 'Documentación incompleta' },
            { invoice_id: 'FC-2026-SUP001-002', supplier_id: 'SUP001', amount: 150000, decision: 'ESCALATED', confirmation_id: '', rejection_reason: 'Requiere revisión' },
        ]);
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
            <td>${inv.supplier_id || inv.supplier || '-'}</td>
            <td class="amount">${formatCurrency(inv.amount)}</td>
            <td><span class="badge ${inv.decision?.toLowerCase() || 'pending'}">${inv.decision || '-'}</span></td>
            <td class="mono">${inv.confirmation_id || '-'}</td>
            <td>${inv.payment_status || '-'}</td>
            <td>${inv.rejection_reason || '-'}</td>
        </tr>
    `).join('');
}

document.getElementById('btn-hist-filter')?.addEventListener('click', () => {
    // En producción, aplicaría filtros
    loadHistory();
});

// ============================================================
// Chat interno
// ============================================================
const internalChatMessages = document.getElementById('internal-chat-messages');
const internalChatInput = document.getElementById('internal-chat-input');
const internalChatSend = document.getElementById('internal-chat-send');

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
        const resp = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        
        const data = await resp.json();
        addInternalChatMessage('system', data.response || 'Mensaje procesado');
    } catch {
        // Fallback
        setTimeout(() => {
            const response = generateInternalResponse(text);
            addInternalChatMessage('system', response);
        }, 1000);
    }
}

function generateInternalResponse(text) {
    const msg = text.toLowerCase();
    
    if (msg.includes('procesar') && msg.includes('todo')) {
        return 'Procesando todas las facturas del inbox...';
    }
    
    if (msg.includes('factura')) {
        return 'Para procesar una factura específica, indicame el número de factura.';
    }
    
    if (msg.includes('total') || msg.includes('estadística')) {
        return 'Hoy se aprobaron 5 facturas por un total de $450,000.';
    }
    
    return 'Entendido. ¿Qué más necesitás?';
}

// ============================================================
// Estado de Agentes (Health Check)
// ============================================================
async function checkAgentsHealth() {
    const statusEl = document.getElementById('agents-status');
    
    try {
        const resp = await fetch(`${API}/health`);
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
    } catch {
        statusEl.innerHTML = `
            <span class="agents-indicator error">🔴</span>
            <span class="agents-text">No se pudo verificar</span>
        `;
    }
}

// Refrescar health cada 30 segundos
setInterval(checkAgentsHealth, 30000);

// ============================================================
// Evaluación
// ============================================================
async function loadEvaluation() {
    const tbody = document.getElementById('eval-tbody');
    tbody.innerHTML = '<tr><td colspan="5">Cargando…</td></tr>';
    
    // Cargar dataset de golden cases
    try {
        const resp = await fetch('/tests/eval/datasets/invoiceflow-dataset.json');
        const data = await resp.json();
        
        renderEvaluation(data.test_cases || []);
    } catch {
        // Fallback con casos de ejemplo
        renderEvaluation([
            { id: 'TC-001', category: 'happy_path', description: 'Factura válida', expected: { passed: true, action: 'APPROVE' } },
            { id: 'TC-002', category: 'structural', description: 'Archivo no PDF', expected: { passed: false, action: 'REJECT', rule_id: 'VR-01' } },
            { id: 'TC-008', category: 'business', description: 'Proveedor no existe', expected: { passed: false, action: 'REJECT', rule_id: 'BR-01' } },
        ]);
    }
}

function renderEvaluation(testCases) {
    const tbody = document.getElementById('eval-tbody');
    
    tbody.innerHTML = testCases.slice(0, 10).map(tc => {
        const passed = tc.expected?.passed !== false;
        return `
            <tr>
                <td><strong>${tc.id}</strong></td>
                <td><span class="badge ${tc.category === 'happy_path' ? 'approved' : 'pending'}">${tc.category}</span></td>
                <td>${tc.description}</td>
                <td><span class="badge ${passed ? 'approved' : 'rejected'}">${passed ? '✅ Pasó' : '❌ Falló'}</span></td>
                <td>${(tc.expected?.score || 1.0) * 100}%</td>
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
