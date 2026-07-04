// InvoiceFlow — Frontend logic
const API = "";  // mismo origen

// ============================================================
// Tabs
// ============================================================
document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
        if (tab.dataset.tab === "dashboard") refreshDashboard();
        if (tab.dataset.tab === "inbox") refreshInbox();
        if (tab.dataset.tab === "history") refreshHistory();
    });
});

// ============================================================
// Health check
// ============================================================
async function checkHealth() {
    try {
        const r = await fetch(`${API}/health`);
        const h = await r.json();
        const dot = document.querySelector("#health-bar .dot");
        const text = document.getElementById("health-text");
        const allOk = Object.values(h.microservices).every(s => s.status === "ok");
        if (allOk) {
            dot.className = "dot ok";
            text.textContent = "Todos los servicios OK";
        } else {
            dot.className = "dot down";
            const down = Object.entries(h.microservices)
                .filter(([_, s]) => s.status !== "ok")
                .map(([n]) => n).join(", ");
            text.textContent = `Servicios caídos: ${down}`;
        }
    } catch (e) {
        document.querySelector("#health-bar .dot").className = "dot down";
        document.getElementById("health-text").textContent = "Backend no responde";
    }
}
checkHealth();
setInterval(checkHealth, 5000);

// ============================================================
// Dashboard
// ============================================================
async function refreshDashboard() {
    try {
        const r = await fetch(`${API}/dashboard`);
        const d = await r.json();
        document.getElementById("stat-inbox").textContent = d.inbox_count;
        document.getElementById("stat-processed").textContent = d.processed_count;
        document.getElementById("stat-rejected").textContent = d.rejected_files;
        document.getElementById("stat-approved").textContent = d.decisions.APPROVED;
        document.getElementById("stat-rejected-decisions").textContent = d.decisions.REJECTED;
        document.getElementById("stat-escalated").textContent = d.decisions.ESCALATED;
        document.getElementById("stat-total").textContent =
            `$${(d.total_amount_approved || 0).toLocaleString("es-AR")}`;

        const tbody = document.querySelector("#recent-table tbody");
        if (d.recent.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">Sin pagos aún</td></tr>';
        } else {
            tbody.innerHTML = d.recent.map(p => `
                <tr>
                    <td>${(p.processed_at || "").slice(0, 19).replace("T", " ")}</td>
                    <td><strong>${p.invoice_id}</strong></td>
                    <td>${p.supplier_id}</td>
                    <td>$${p.amount.toLocaleString("es-AR")}</td>
                    <td><span class="badge ${p.decision.toLowerCase()}">${p.decision}</span></td>
                    <td>${p.payment_status}</td>
                </tr>
            `).join("");
        }
    } catch (e) {
        toast("Error cargando dashboard", "error");
    }
}

// ============================================================
// Inbox
// ============================================================
async function refreshInbox() {
    try {
        const r = await fetch(`${API}/inbox`);
        const items = await r.json();
        const tbody = document.querySelector("#inbox-table tbody");
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-light);padding:32px">📭 Inbox vacío. Subí una factura o copiala a la carpeta inbox.</td></tr>';
        } else {
            tbody.innerHTML = items.map(it => `
                <tr>
                    <td><code>${it.filename}</code></td>
                    <td>${it.invoice_id || "?"}</td>
                    <td>${it.supplier_id || "?"}</td>
                    <td>${it.amount || "?"}</td>
                    <td>${(it.size / 1024).toFixed(1)} KB</td>
                    <td>
                        <button class="btn-primary btn-small" onclick="processOne('${it.filename}')">
                            ▶️ Procesar
                        </button>
                    </td>
                </tr>
            `).join("");
        }
    } catch (e) {
        toast("Error cargando inbox", "error");
    }
}

async function processOne(filename) {
    if (!confirm(`¿Procesar la factura ${filename}?`)) return;
    try {
        const r = await fetch(`${API}/inbox/process/${encodeURIComponent(filename)}`, {
            method: "POST",
        });
        if (!r.ok) {
            const err = await r.json();
            toast(`Error: ${err.detail || r.statusText}`, "error");
            return;
        }
        const result = await r.json();
        const decisionLabel = result.decision;
        toast(`✅ ${result.invoice_id}: ${decisionLabel} (${result.payment_status})`, "success");
        refreshInbox();
        refreshDashboard();
    } catch (e) {
        toast(`Error: ${e.message}`, "error");
    }
}

async function processAll() {
    if (!confirm("¿Procesar TODAS las facturas del inbox?")) return;
    try {
        const r = await fetch(`${API}/inbox/process-all`, { method: "POST" });
        const result = await r.json();
        const ok = result.results.filter(x => x.decision).length;
        const err = result.results.length - ok;
        toast(`Procesadas ${result.processed}: ${ok} OK, ${err} con error`, err === 0 ? "success" : "error");
        refreshInbox();
        refreshDashboard();
    } catch (e) {
        toast(`Error: ${e.message}`, "error");
    }
}

document.getElementById("process-all-btn").addEventListener("click", processAll);
document.getElementById("refresh-inbox-btn").addEventListener("click", refreshInbox);

// Upload
document.getElementById("upload-btn").addEventListener("click", async () => {
    const fileInput = document.getElementById("upload-file");
    if (!fileInput.files.length) {
        toast("Seleccioná un archivo primero", "error");
        return;
    }
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    try {
        const r = await fetch(`${API}/inbox/upload`, {
            method: "POST",
            body: formData,
        });
        const result = await r.json();
        if (!r.ok) {
            toast(`Error: ${result.detail || r.statusText}`, "error");
            return;
        }
        toast(`✅ ${result.filename} subido al inbox`, "success");
        fileInput.value = "";
        refreshInbox();
    } catch (e) {
        toast(`Error: ${e.message}`, "error");
    }
});

// ============================================================
// Chat
// ============================================================
const chatMessages = document.getElementById("chat-messages");

function addChatMsg(role, text, data = null) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    const time = new Date().toLocaleTimeString("es-AR");
    let html = `<div class="meta">${role === "user" ? "Tú" : "Sistema"} · ${time}</div>
                <div>${text.replace(/\n/g, "<br>")}</div>`;
    if (data) {
        html += `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    }
    div.innerHTML = html;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChat() {
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;
    addChatMsg("user", msg);
    input.value = "";
    try {
        const r = await fetch(`${API}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg }),
        });
        const result = await r.json();
        addChatMsg("system", result.message, result.data);
    } catch (e) {
        addChatMsg("system", `Error: ${e.message}`);
    }
}

document.getElementById("chat-send").addEventListener("click", sendChat);
document.getElementById("chat-input").addEventListener("keypress", e => {
    if (e.key === "Enter") sendChat();
});

// Welcome message
addChatMsg("system",
    "👋 Hola! Soy el sistema InvoiceFlow. Decime qué factura procesar.\n" +
    "Probá con: 'qué hay en el inbox?' o 'procesá todo el inbox'.");

// ============================================================
// History
// ============================================================
let currentFilter = "";
document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentFilter = btn.dataset.decision;
        refreshHistory();
    });
});

async function refreshHistory() {
    try {
        const url = currentFilter
            ? `${API}/invoices?decision=${currentFilter}`
            : `${API}/invoices?limit=100`;
        const r = await fetch(url);
        const items = await r.json();
        const tbody = document.querySelector("#history-table tbody");
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-light);padding:32px">Sin resultados</td></tr>';
        } else {
            tbody.innerHTML = items.map(p => `
                <tr>
                    <td>${(p.processed_at || "").slice(0, 19).replace("T", " ")}</td>
                    <td><strong>${p.invoice_id}</strong></td>
                    <td>${p.supplier_id}</td>
                    <td>$${p.amount.toLocaleString("es-AR")}</td>
                    <td><span class="badge ${p.decision.toLowerCase()}">${p.decision}</span></td>
                    <td><code style="font-size:11px">${p.confirmation_id}</code></td>
                    <td>${p.payment_status}</td>
                    <td style="max-width:300px">${p.rejection_reason || "—"}</td>
                </tr>
            `).join("");
        }
    } catch (e) {
        toast("Error cargando historial", "error");
    }
}

// ============================================================
// Toast
// ============================================================
function toast(msg, type = "success") {
    const div = document.createElement("div");
    div.className = `toast ${type}`;
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

// ============================================================
// Modal de facturas
// ============================================================
let grouperResult = null;

function openInvoicesModal() {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "invoices-modal";
    
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>Gestión de Facturas</h3>
                <button class="modal-close" onclick="closeInvoicesModal()">&times;</button>
            </div>
            <div class="modal-body" id="modal-body">
                <p style="color: var(--text-light); margin-bottom: 16px;">Cargando facturas...</p>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeInvoicesModal()">Cerrar</button>
                <button class="btn-primary" id="btn-run-grouper" onclick="runGrouper()">
                    📁 Ejecutar Agente Agrupador
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    loadInvoicesForModal();
}

function closeInvoicesModal() {
    const modal = document.getElementById("invoices-modal");
    if (modal) modal.remove();
}

async function loadInvoicesForModal() {
    try {
        const r = await fetch(`${API}/new-invoices`);
        const data = await r.json();
        const body = document.getElementById("modal-body");
        
        if (!data.files || data.files.length === 0) {
            body.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-light);">
                    <p style="font-size: 48px; margin-bottom: 12px;">📁</p>
                    <p>No hay facturas pendientes en la carpeta "new invoices".</p>
                </div>
            `;
            document.getElementById("btn-run-grouper").style.display = "none";
            return;
        }
        
        body.innerHTML = `
            <p style="margin-bottom: 16px; color: var(--text-light); font-size: 13px;">
                Facturas pendientes en la carpeta "new invoices": ${data.files.length}
            </p>
            <div class="invoice-list" id="invoice-list">
                ${data.files.map(f => `
                    <div class="invoice-item">
                        <div class="invoice-info">
                            <h4>${f.filename}</h4>
                            <p>${f.supplier_id ? 'Proveedor: ' + f.supplier_id : 'Proveedor no identificado'} · ${f.size_kb} KB</p>
                        </div>
                        <div class="invoice-actions">
                            <button class="btn-secondary btn-small" onclick="viewInvoice('${f.filename}')">Ver</button>
                        </div>
                    </div>
                `).join("")}
            </div>
            <div id="grouper-result-container"></div>
        `;
        
    } catch (e) {
        document.getElementById("modal-body").innerHTML = `
            <p style="color: var(--rejected);">Error cargando facturas: ${e.message}</p>
        `;
    }
}

async function viewInvoice(filename) {
    try {
        const r = await fetch(`${API}/new-invoices/content?filename=${encodeURIComponent(filename)}`);
        const data = await r.json();
        
        const body = document.getElementById("modal-body");
        body.innerHTML = `
            <h4 style="margin-bottom: 12px;">${filename}</h4>
            <pre style="background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 6px; font-size: 12px; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">${data.content || 'Contenido no disponible'}</pre>
            <button class="btn-secondary" onclick="loadInvoicesForModal()" style="margin-top: 16px;">← Volver a la lista</button>
        `;
    } catch (e) {
        toast("Error cargando factura: " + e.message, "error");
    }
}

async function runGrouper() {
    const btn = document.getElementById("btn-run-grouper");
    btn.disabled = true;
    btn.textContent = "⏳ Procesando...";
    
    try {
        const r = await fetch(`${API}/group-invoices`, { method: "POST" });
        const result = await r.json();
        
        grouperResult = result;
        
        const container = document.getElementById("grouper-result-container");
        container.innerHTML = `
            <div class="grouper-result">
                <h4>Resultado del Agente Agrupador</h4>
                <div class="grouper-stat">
                    <span style="color: #16a34a;">✓</span>
                    <span>Facturas movidas: ${result.moved_count}</span>
                </div>
                ${Object.keys(result.grouped_by_cuit || {}).length > 0 ? `
                    <h4 style="margin-top: 12px;">Carpetas creadas:</h4>
                    ${Object.entries(result.grouped_by_cuit).map(([cuit, files]) => `
                        <div class="grouper-folder">
                            <div class="grouper-folder-title">CUIT-${cuit}</div>
                            <div class="grouper-folder-files">${Array.isArray(files) ? files.join(', ') : 'Archivos movidos'}</div>
                        </div>
                    `).join("")}
                ` : ''}
            </div>
        `;
        
        toast("Agrupación completada: " + result.moved_count + " facturas movidas", "success");
        
        // Recargar lista
        setTimeout(() => {
            loadInvoicesForModal();
        }, 1500);
        
    } catch (e) {
        toast("Error ejecutando agrupador: " + e.message, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "📁 Ejecutar Agente Agrupador";
    }
}

// Event listeners para los botones del header
document.getElementById("btn-ver-facturas").addEventListener("click", openInvoicesModal);
document.getElementById("btn-agrupar").addEventListener("click", runGrouper);

// Initial load
refreshDashboard();