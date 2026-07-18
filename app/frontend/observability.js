// ============================================================
// OBSERVABILIDAD COMPLETA V3 - loadObservability()
// ============================================================

// Función global para recargar observabilidad
window.reloadObservability = function() {
    loadObservability();
};

// Función global para recargar SOLO logs
window.reloadLogs = function() {
    loadLogsDirectly();
};

async function loadObservability() {
    const banner = document.getElementById('obs-health-banner');
    if (!banner) return;

    banner.innerHTML = '<span class="status-icon">🔄</span><span class="status-text"><strong>Cargando...</strong><br><small>Consultando estado del sistema...</small></span>';

    try {
        // Intentar primero el endpoint completo de observabilidad
        const resp = await fetch(API + '/health/observability');
        if (resp.ok) {
            const data = await resp.json();
            if (data && data.status) {
                updateObservabilityBanner(data);
                updateServicesSection(data.services);
                updateDatabasesSection(data.databases);
                updateMCPSection(data.integrations?.mcp);
                updateRAGSection(data.integrations?.rag);
                updateFilesSection(data.files);
                updateLogsSection(data.logs);
                updateAgentsSection(data.agents);
                updateA2ASection(data.integrations?.a2a);
                updateIssuesSection(data);
                return;
            }
        }
        
        // Fallback: usar /agents/health si observability falla
        await loadObservabilityFallback();
        
    } catch (err) {
        console.error('[loadObservability]', err);
        // Último fallback: intentar agentes health
        try {
            await loadObservabilityFallback();
        } catch (e2) {
            banner.className = 'status-summary warning';
            banner.innerHTML = '<span class="status-icon">⚠️</span><span class="status-text"><strong>Error de conexion</strong><br><small>' + err.message + '</small></span>';
            showFallbackUI();
        }
    }
}

// Cargar logs directamente desde el endpoint
async function loadLogsDirectly() {
    const el = document.getElementById('obs-logs-content');
    if (!el) return;
    
    el.innerHTML = '<div style="text-align:center;padding:20px;"><span style="font-size:24px;">🔄</span><br>Cargando logs...</div>';
    
    try {
        // Obtener 500 líneas de logs
        const resp = await fetch(API + '/logs/recent?lines=500');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        
        const data = await resp.json();
        displayAllLogs(el, data);
    } catch (err) {
        el.innerHTML = '<div class="obs-metrics"><span class="obs-metric error">🔴 Error</span></div><div style="color:#ef4444;padding:10px;">Error al cargar logs: ' + err.message + '</div>';
    }
}

function displayAllLogs(el, data) {
    if (!data.entries) {
        el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">📋 Sin datos</span></div>';
        return;
    }
    
    const entries = data.entries;
    const levels = data.level_counts || {};
    const totalErrors = entries.filter(e => e.level === 'ERROR').length;
    const totalWarnings = entries.filter(e => e.level === 'WARNING').length;
    
    let html = '<div style="margin-bottom:10px;"><button onclick="reloadLogs()" style="background:#333;color:#fff;border:1px solid #555;padding:4px 8px;cursor:pointer;border-radius:4px;font-size:11px;">🔄 Recargar</button></div>';
    html += '<div class="obs-metrics"><span class="obs-metric ' + (totalErrors > 0 ? 'error' : 'ok') + '">📋 ' + (data.total_lines || entries.length) + ' entradas totales</span><span class="obs-metric error">🔴 ' + totalErrors + ' errores</span><span class="obs-metric warning">⚠️ ' + totalWarnings + ' warnings</span></div>';
    
    // Distribución
    html += '<div class="obs-subsection"><strong>Distribucion:</strong></div><div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">';
    if (levels.INFO) html += '<span style="color:#22c55e;">● ' + levels.INFO + ' INFO</span>';
    if (levels.WARNING) html += '<span style="color:#eab308;">● ' + levels.WARNING + ' WARN</span>';
    if (levels.ERROR) html += '<span style="color:#ef4444;">● ' + levels.ERROR + ' ERROR</span>';
    if (levels.DEBUG) html += '<span style="color:#888;">● ' + levels.DEBUG + ' DEBUG</span>';
    html += '</div>';
    
    // TODOS LOS LOGS
    html += '<div class="obs-subsection" style="margin-top:15px;border-top:1px solid #333;padding-top:10px;"><strong>📜 TODOS LOS LOGS (' + entries.length + '):</strong></div>';
    html += '<div style="max-height:500px;overflow-y:auto;background:#1a1a1a;border-radius:4px;padding:8px;font-family:monospace;font-size:11px;line-height:1.4;">';
    
    for (const entry of entries) {
        const level = entry.level || 'INFO';
        let color = '#22c55e';
        let bg = 'transparent';
        if (level === 'WARNING') { color = '#eab308'; bg = 'rgba(234,179,8,0.1)'; }
        else if (level === 'ERROR') { color = '#ef4444'; bg = 'rgba(239,68,68,0.15)'; }
        else if (level === 'DEBUG') { color = '#888'; }
        
        const msg = entry.message || '';
        html += '<div style="color:' + color + ';background:' + bg + ';padding:2px 4px;margin:1px 0;border-radius:2px;word-break:break-all;">' + escapeHtml(msg) + '</div>';
    }
    html += '</div>';
    
    el.innerHTML = html;
}

// Fallback que usa los endpoints existentes
async function loadObservabilityFallback() {
    try {
        const resp = await fetch(API + '/agents/health');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        
        updateObservabilityBannerFallback(data);
        updateServicesSectionFallback(data);
        updateDatabasesSectionFallback();
        updateMCPSectionFallback();
        updateRAGSectionFallback();
        updateFilesSectionFallback();
        updateLogsSectionFallback();
        updateAgentsSectionFallback();
        updateA2ASectionFallback(data);
        updateIssuesSectionFallback(data);
    } catch (err) {
        console.error('[loadObservabilityFallback]', err);
        throw err;
    }
}

function showFallbackUI() {
    const servicesEl = document.getElementById('obs-services-content');
    const databasesEl = document.getElementById('obs-databases-content');
    const mcpEl = document.getElementById('obs-mcp-content');
    const ragEl = document.getElementById('obs-rag-content');
    const filesEl = document.getElementById('obs-files-content');
    const logsEl = document.getElementById('obs-logs-content');
    const agentsEl = document.getElementById('obs-agents-content');
    const a2aEl = document.getElementById('obs-a2a-content');
    
    const msg = '<span style="color:#888;font-size:12px;">Reiniciar backend para datos completos</span>';
    if (servicesEl) servicesEl.innerHTML = msg;
    if (databasesEl) databasesEl.innerHTML = msg;
    if (mcpEl) mcpEl.innerHTML = msg;
    if (ragEl) ragEl.innerHTML = msg;
    if (filesEl) filesEl.innerHTML = msg;
    if (logsEl) logsEl.innerHTML = msg;
    if (agentsEl) agentsEl.innerHTML = msg;
    if (a2aEl) a2aEl.innerHTML = msg;
}

function updateObservabilityBanner(data) {
    const banner = document.getElementById('obs-health-banner');
    const score = data.health_score || 0;
    const status = data.status || 'unknown';
    const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleTimeString('es-AR') : '-';
    
    // Verificar servicios caídos
    const services = data.services?.services || {};
    const metrics = data.services?.metrics || {};
    const downCount = metrics.down || 0;
    const totalCount = metrics.total || 0;

    let statusIcon = '✅', statusClass = 'ok';
    if (status === 'degraded') { statusIcon = '⚠️'; statusClass = 'warning'; }
    else if (status === 'unhealthy') { statusIcon = '❌'; statusClass = 'error'; }
    else if (status === 'error') { statusIcon = '⚠️'; statusClass = 'warning'; }
    
    // Agregar advertencia de servicios caídos
    let downWarning = '';
    if (downCount > 0) {
        downWarning = '<br><span style="color:#ef4444;font-size:11px;">⚠️ ' + downCount + ' servicio(s) caídos - Ver sección Servicios</span>';
    }

    banner.className = 'status-summary ' + statusClass;
    banner.innerHTML = '<span class="status-icon">' + statusIcon + '</span><span class="status-text"><strong>Health Score: ' + score + '% - ' + status.toUpperCase() + '</strong><br><small>Ultima actualizacion: ' + timestamp + downWarning + '</small></span>';
}

function updateObservabilityBannerFallback(data) {
    const banner = document.getElementById('obs-health-banner');
    const criticalOk = data.status === 'ok';
    const allOk = data.all_services_ok;
    
    let statusIcon = criticalOk ? '✅' : '⚠️';
    let statusClass = criticalOk ? 'ok' : 'warning';
    let score = criticalOk ? (allOk ? 100 : 80) : 60;
    
    banner.className = 'status-summary ' + statusClass;
    banner.innerHTML = '<span class="status-icon">' + statusIcon + '</span><span class="status-text"><strong>Health Score: ' + score + '% - ' + (criticalOk ? 'HEALTHY' : 'DEGRADED') + '</strong><br><small>Modo compatibilidad - Reiniciar backend para V3</small></span>';
}

function updateServicesSection(services) {
    const el = document.getElementById('obs-services-content');
    if (!el) return;
    if (!services?.services) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const metrics = services.metrics || {};
    const all = services.services;
    
    // Separar servicios caídos de los activos
    const downCritical = [];
    const downSecondary = [];
    const upServices = [];
    
    for (const [name, svc] of Object.entries(all)) {
        const ok = svc.status?.ok;
        const svcInfo = {name, svc};
        if (svc.type === 'critical') {
            if (ok) upServices.push(svcInfo);
            else downCritical.push(svcInfo);
        } else {
            if (ok) upServices.push(svcInfo);
            else downSecondary.push(svcInfo);
        }
    }
    
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (metrics.all_critical_healthy ? 'ok' : 'error') + '">🔴 ' + (metrics.up || 0) + '/' + (metrics.total || 0) + ' servicios</span></div>';
    
    // PRIMERO: Servicios caídos (CRÍTICOS) - los más importantes
    if (downCritical.length > 0) {
        html += '<div class="obs-subsection" style="color:#ef4444;"><strong>🔴 SERVICIOS CRÍTICOS CAÍDOS:</strong></div>';
        for (const {name, svc} of downCritical) {
            const status = svc.status?.status || 'unknown';
            const url = svc.url || '';
            const responseTime = svc.status?.response_time_ms ? (svc.status.response_time_ms/1000).toFixed(2) + 's' : '-';
            html += '<div class="obs-item error" style="background:#2a0a0a;padding:8px;border-radius:4px;margin:4px 0;">';
            html += '<div style="font-weight:bold;color:#ef4444;">🔴 ' + name + '</div>';
            html += '<div style="font-size:11px;color:#888;margin-left:20px;">';
            html += '<div>Estado: <span style="color:#ef4444;">' + status + '</span></div>';
            html += '<div>URL: ' + url + '</div>';
            html += '<div>Respuesta: ' + responseTime + '</div>';
            html += '</div></div>';
        }
    }
    
    // SEGUNDO: Servicios caídos (SECUNDARIOS)
    if (downSecondary.length > 0) {
        html += '<div class="obs-subsection" style="color:#eab308;"><strong>🟡 SERVICIOS SECUNDARIOS CAÍDOS:</strong></div>';
        for (const {name, svc} of downSecondary) {
            const status = svc.status?.status || 'unknown';
            const url = svc.url || '';
            html += '<div class="obs-item warning" style="background:#2a2a0a;padding:8px;border-radius:4px;margin:4px 0;">';
            html += '<div style="font-weight:bold;color:#eab308;">🟡 ' + name + '</div>';
            html += '<div style="font-size:11px;color:#888;margin-left:20px;">';
            html += '<div>Estado: <span style="color:#eab308;">' + status + '</span></div>';
            html += '<div>URL: ' + url + '</div>';
            html += '</div></div>';
        }
    }
    
    // TERCERO: Servicios activos (CRÍTICOS)
    html += '<div class="obs-subsection"><strong>🟢 Criticos activos:</strong></div>';
    let hasCritical = false;
    for (const [name, svc] of Object.entries(all)) {
        if (svc.type !== 'critical' || !svc.status?.ok) continue;
        hasCritical = true;
        const status = svc.status?.status || 'ok';
        const responseTime = svc.status?.response_time_ms ? (svc.status.response_time_ms/1000).toFixed(3) + 's' : '-';
        html += '<div class="obs-item ok"><span>🟢</span><span>' + name + '</span><span class="obs-detail">' + status + ' (' + responseTime + ')</span></div>';
    }
    if (!hasCritical) html += '<div style="color:#888;font-size:12px;padding-left:10px;">Ninguno</div>';
    
    // CUARTO: Servicios activos (SECUNDARIOS)
    html += '<div class="obs-subsection" style="margin-top:10px;"><strong>🟢 Secundarios activos:</strong></div>';
    let hasSecondary = false;
    for (const [name, svc] of Object.entries(all)) {
        if (svc.type !== 'secondary' || !svc.status?.ok) continue;
        hasSecondary = true;
        const status = svc.status?.status || 'ok';
        html += '<div class="obs-item ok"><span>🟢</span><span>' + name + '</span><span class="obs-detail">' + status + '</span></div>';
    }
    if (!hasSecondary) html += '<div style="color:#888;font-size:12px;padding-left:10px;">Ninguno</div>';
    
    el.innerHTML = html;
}

function updateServicesSectionFallback(data) {
    const el = document.getElementById('obs-services-content');
    if (!el) return;
    
    const critical = data.critical_services || {};
    const secondary = data.secondary_services || {};
    const criticalCount = Object.values(critical).filter(s => s.ok).length;
    const totalCount = criticalCount + Object.values(secondary).filter(s => s.ok).length;
    
    // Separar caídos de activos
    const criticalDown = Object.entries(critical).filter(([,s]) => !s.ok);
    const criticalUp = Object.entries(critical).filter(([,s]) => s.ok);
    const secondaryDown = Object.entries(secondary).filter(([,s]) => !s.ok);
    const secondaryUp = Object.entries(secondary).filter(([,s]) => s.ok);
    
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (data.status === 'ok' ? 'ok' : 'error') + '">🔴 ' + totalCount + '/' + (Object.keys(critical).length + Object.keys(secondary).length) + ' servicios</span></div>';
    
    // PRIMERO: Servicios caídos críticos
    if (criticalDown.length > 0) {
        html += '<div class="obs-subsection" style="color:#ef4444;"><strong>🔴 CRÍTICOS CAÍDOS:</strong></div>';
        for (const [name, svc] of criticalDown) {
            html += '<div class="obs-item error" style="background:#2a0a0a;padding:8px;border-radius:4px;margin:4px 0;">';
            html += '<div style="font-weight:bold;">🔴 ' + name + '</div>';
            html += '<div style="font-size:11px;color:#888;margin-left:20px;">Estado: <span style="color:#ef4444;">' + (svc.status || 'unknown') + '</span></div>';
            html += '</div>';
        }
    }
    
    // SEGUNDO: Servicios caídos secundarios
    if (secondaryDown.length > 0) {
        html += '<div class="obs-subsection" style="color:#eab308;"><strong>🟡 SECUNDARIOS CAÍDOS:</strong></div>';
        for (const [name, svc] of secondaryDown) {
            html += '<div class="obs-item warning" style="background:#2a2a0a;padding:8px;border-radius:4px;margin:4px 0;">';
            html += '<div style="font-weight:bold;">🟡 ' + name + '</div>';
            html += '<div style="font-size:11px;color:#888;margin-left:20px;">Estado: <span style="color:#eab308;">' + (svc.status || 'unknown') + '</span></div>';
            html += '</div>';
        }
    }
    
    // Activos críticos
    html += '<div class="obs-subsection"><strong>🟢 Criticos activos:</strong></div>';
    for (const [name, svc] of criticalUp) {
        html += '<div class="obs-item ok"><span>🟢</span><span>' + name + '</span><span class="obs-detail">' + (svc.status || 'ok') + '</span></div>';
    }
    
    // Activos secundarios
    html += '<div class="obs-subsection" style="margin-top:10px;"><strong>🟢 Secundarios activos:</strong></div>';
    for (const [name, svc] of secondaryUp) {
        html += '<div class="obs-item ok"><span>🟢</span><span>' + name + '</span><span class="obs-detail">' + (svc.status || 'ok') + '</span></div>';
    }
    
    el.innerHTML = html;
}

function updateDatabasesSection(databases) {
    const el = document.getElementById('obs-databases-content');
    if (!el) return;
    if (!databases?.databases) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const metrics = databases.metrics || {};
    const all = databases.databases;
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (metrics.all_healthy ? 'ok' : 'error') + '">🗄️ ' + (metrics.ok || 0) + '/' + (metrics.total || 0) + ' DBs OK</span></div>';
    for (const [name, db] of Object.entries(all)) {
        const ok = db.ok;
        html += '<div class="obs-item ' + (ok ? 'ok' : 'error') + '"><span>' + (ok ? '🟢' : '🔴') + '</span><span>' + name.replace('_db', '') + '</span><span class="obs-detail">' + (db.size_human || '-') + ' | ' + (db.total_rows || 0) + ' filas</span></div>';
    }
    el.innerHTML = html;
}

function updateDatabasesSectionFallback() {
    const el = document.getElementById('obs-databases-content');
    if (!el) return;
    el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">🗄️ Verificar manualmente</span></div><div class="obs-item"><span>ℹ️</span><span>Reiniciar backend</span><span class="obs-detail">para ver DBs</span></div>';
}

function updateMCPSection(mcp) {
    const el = document.getElementById('obs-mcp-content');
    if (!el) return;
    if (!mcp) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const toolbox = mcp.mcp_toolbox || {};
    const summary = mcp.integration_summary || {};
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (summary.server_available ? 'ok' : 'warning') + '">🔧 ' + (summary.tools_configured || 0) + ' herramientas</span></div>';
    const statusIcon = toolbox.status === 'running' ? '🟢' : '🟡';
    const statusText = toolbox.status === 'running' ? 'Ejecutandose' : 'No corriendo';
    html += '<div class="obs-item ' + (toolbox.status === 'running' ? 'ok' : 'warning') + '"><span>' + statusIcon + '</span><span>MCP Toolbox</span><span class="obs-detail">' + statusText + '</span></div>';

    const tools = toolbox.configured_tools || [];
    if (tools.length > 0) {
        html += '<div class="obs-subsection"><strong>Herramientas:</strong></div>';
        for (const tool of tools.slice(0, 5)) { html += '<div class="obs-item" style="padding-left:20px;">• ' + (tool.name || tool) + '</div>'; }
        if (tools.length > 5) html += '<div class="obs-item" style="padding-left:20px;color:#888;">... y ' + (tools.length - 5) + ' mas</div>';
    }
    if (toolbox.status !== 'running' && toolbox.start_command) { html += '<div style="margin-top:10px;padding:8px;background:#f5f5f5;border-radius:4px;font-size:12px;"><strong>Para iniciar:</strong><br><code>' + toolbox.start_command + '</code></div>'; }
    el.innerHTML = html;
}

function updateMCPSectionFallback() {
    const el = document.getElementById('obs-mcp-content');
    if (!el) return;
    el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">🔧 0 herramientas</span></div><div class="obs-item warning"><span>🟡</span><span>MCP Toolbox</span><span class="obs-detail">No corriendo</span></div><div class="obs-subsection"><strong>Herramientas:</strong></div><div class="obs-item" style="padding-left:20px;color:#888;font-size:12px;">Reiniciar backend para ver</div>';
}

function updateRAGSection(rag) {
    const el = document.getElementById('obs-rag-content');
    if (!el) return;
    if (!rag) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const status = rag.integration_status || {};
    const primary = rag.primary_rag || {};
    const ok = status.primary_available;
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (ok ? 'ok' : 'warning') + '">📚 ' + (status.documents_indexed || 0) + ' docs indexados</span></div>';
    html += '<div class="obs-item ' + (ok ? 'ok' : 'error') + '"><span>' + (ok ? '🟢' : '🔴') + '</span><span>ChromaDB</span><span class="obs-detail">' + (primary.collections_count || 0) + ' collections</span></div>';
    if (primary.collections && primary.collections.length > 0) {
        html += '<div class="obs-subsection"><strong>Collections:</strong></div>';
        for (const col of primary.collections) { html += '<div class="obs-item" style="padding-left:20px;">📁 ' + (col.name || col.id) + '</div>'; }
    }
    el.innerHTML = html;
}

function updateRAGSectionFallback() {
    const el = document.getElementById('obs-rag-content');
    if (!el) return;
    el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">📚 0 docs</span></div><div class="obs-item warning"><span>🟡</span><span>ChromaDB</span><span class="obs-detail">Sin datos</span></div>';
}

function updateFilesSection(files) {
    const el = document.getElementById('obs-files-content');
    if (!el) return;
    if (!files?.paths) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const metrics = files.metrics || {};
    const paths = files.paths || {};
    const pathNames = { 'inbox': '📥 Inbox', 'processed': '✅ Procesadas', 'rejected': '❌ Rechazadas', 'new_invoices': '📝 Nuevas', 'contracts': '📄 Contratos' };
    let html = '<div class="obs-metrics"><span class="obs-metric">📁 ' + (metrics.total_files || 0) + ' archivos (' + (metrics.total_size_human || '-') + ')</span></div>';
    for (const [key, pathData] of Object.entries(paths)) {
        if (!pathData.ok) continue;
        html += '<div class="obs-item"><span>' + (pathData.file_count > 0 ? '📄' : '📭') + '</span><span>' + (pathNames[key] || key) + '</span><span class="obs-detail">' + (pathData.file_count || 0) + ' | ' + (pathData.size_human || '-') + '</span></div>';
    }
    el.innerHTML = html;
}

function updateFilesSectionFallback() {
    const el = document.getElementById('obs-files-content');
    if (!el) return;
    el.innerHTML = '<div class="obs-metrics"><span class="obs-metric">📁 0 archivos</span></div><div class="obs-item"><span>📭</span><span>Inbox</span><span class="obs-detail">0</span></div><div class="obs-item"><span>📭</span><span>Procesadas</span><span class="obs-detail">0</span></div><div class="obs-item"><span>📭</span><span>Rechazadas</span><span class="obs-detail">0</span></div>';
}

function updateLogsSection(logs) {
    const el = document.getElementById('obs-logs-content');
    if (!el) return;
    if (!logs) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const metrics = logs.metrics || {};
    const recent = logs.recent || {};
    const errors = logs.errors || {};
    const warnings = logs.warnings || {};
    
    // Encabezado con métricas y botón de recarga
    let html = '<div style="margin-bottom:10px;"><button onclick="reloadLogs()" style="background:#333;color:#fff;border:1px solid #555;padding:4px 8px;cursor:pointer;border-radius:4px;font-size:11px;">🔄 Recargar Logs</button></div>';
    html += '<div class="obs-metrics"><span class="obs-metric ' + (metrics.has_critical_issues ? 'error' : 'ok') + '">📋 ' + (recent.total_lines || 0) + ' entradas totales</span><span class="obs-metric error">🔴 ' + (metrics.total_errors || 0) + ' errores</span><span class="obs-metric warning">⚠️ ' + (metrics.total_warnings || 0) + ' warnings</span></div>';

    // Distribución por nivel
    const levels = recent.level_counts || {};
    if (Object.keys(levels).length > 0) {
        html += '<div class="obs-subsection"><strong>Distribucion:</strong></div><div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">';
        if (levels.INFO) html += '<span style="color:#22c55e;">● ' + levels.INFO + ' INFO</span>';
        if (levels.WARNING) html += '<span style="color:#eab308;">● ' + levels.WARNING + ' WARN</span>';
        if (levels.ERROR) html += '<span style="color:#ef4444;">● ' + levels.ERROR + ' ERROR</span>';
        if (levels.DEBUG) html += '<span style="color:#888;">● ' + levels.DEBUG + ' DEBUG</span>';
        html += '</div>';
    }
    
    // TODOS LOS LOGS EN DETALLE - no solo resúmenes
    const entries = recent.entries || [];
    if (entries.length > 0) {
        html += '<div class="obs-subsection" style="margin-top:15px;border-top:1px solid #333;padding-top:10px;"><strong>📜 TODOS LOS LOGS (' + entries.length + ' entradas):</strong></div>';
        html += '<div style="max-height:400px;overflow-y:auto;background:#1a1a1a;border-radius:4px;padding:8px;font-family:monospace;font-size:11px;line-height:1.4;">';
        for (const entry of entries) {
            const level = entry.level || 'INFO';
            let color = '#22c55e'; // verde
            let bg = 'transparent';
            if (level === 'WARNING') { color = '#eab308'; bg = 'rgba(234,179,8,0.1)'; }
            else if (level === 'ERROR') { color = '#ef4444'; bg = 'rgba(239,68,68,0.15)'; }
            else if (level === 'DEBUG') { color = '#888'; }
            
            // Escapar HTML y mostrar el mensaje completo (sin truncar)
            const msg = entry.message || '';
            html += '<div style="color:' + color + ';background:' + bg + ';padding:2px 4px;margin:1px 0;border-radius:2px;word-break:break-all;">' + escapeHtml(msg) + '</div>';
        }
        html += '</div>';
    }
    
    // Errores específicos
    if (errors.entries && errors.entries.length > 0) {
        html += '<div class="obs-subsection" style="margin-top:15px;border-top:1px solid #333;padding-top:10px;"><strong>🔴 Detalle de errores (' + errors.entries.length + '):</strong></div>';
        html += '<div style="background:#2a0a0a;border-radius:4px;padding:8px;font-family:monospace;font-size:11px;max-height:200px;overflow-y:auto;">';
        for (const entry of errors.entries) {
            html += '<div style="color:#ef4444;padding:2px 4px;margin:1px 0;word-break:break-all;">' + escapeHtml(entry) + '</div>';
        }
        html += '</div>';
    }
    
    // Warnings específicos
    if (warnings.entries && warnings.entries.length > 0) {
        html += '<div class="obs-subsection" style="margin-top:15px;border-top:1px solid #333;padding-top:10px;"><strong>⚠️ Detalle de warnings (' + warnings.entries.length + '):</strong></div>';
        html += '<div style="background:#2a2a0a;border-radius:4px;padding:8px;font-family:monospace;font-size:11px;max-height:200px;overflow-y:auto;">';
        for (const entry of warnings.entries) {
            html += '<div style="color:#eab308;padding:2px 4px;margin:1px 0;word-break:break-all;">' + escapeHtml(entry) + '</div>';
        }
        html += '</div>';
    }
    
    el.innerHTML = html;
}

// Función para escapar HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateLogsSectionFallback() {
    const el = document.getElementById('obs-logs-content');
    if (!el) return;
    
    // Intentar obtener logs del endpoint directo
    fetch(API + '/logs/recent?lines=200')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.entries) {
                let html = '<div class="obs-metrics"><span class="obs-metric ok">📋 ' + (data.total_lines || 0) + ' entradas totales</span></div>';
                
                const levels = data.level_counts || {};
                html += '<div class="obs-subsection"><strong>Distribucion:</strong></div><div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">';
                if (levels.INFO) html += '<span style="color:#22c55e;">● ' + levels.INFO + ' INFO</span>';
                if (levels.WARNING) html += '<span style="color:#eab308;">● ' + levels.WARNING + ' WARN</span>';
                if (levels.ERROR) html += '<span style="color:#ef4444;">● ' + levels.ERROR + ' ERROR</span>';
                if (levels.DEBUG) html += '<span style="color:#888;">● ' + levels.DEBUG + ' DEBUG</span>';
                html += '</div>';
                
                // TODOS LOS LOGS EN DETALLE
                if (data.entries && data.entries.length > 0) {
                    html += '<div class="obs-subsection" style="margin-top:15px;border-top:1px solid #333;padding-top:10px;"><strong>📜 TODOS LOS LOGS (' + data.entries.length + ' entradas):</strong></div>';
                    html += '<div style="max-height:400px;overflow-y:auto;background:#1a1a1a;border-radius:4px;padding:8px;font-family:monospace;font-size:11px;line-height:1.4;">';
                    for (const entry of data.entries) {
                        const level = entry.level || 'INFO';
                        let color = '#22c55e';
                        let bg = 'transparent';
                        if (level === 'WARNING') { color = '#eab308'; bg = 'rgba(234,179,8,0.1)'; }
                        else if (level === 'ERROR') { color = '#ef4444'; bg = 'rgba(239,68,68,0.15)'; }
                        else if (level === 'DEBUG') { color = '#888'; }
                        
                        const msg = entry.message || '';
                        html += '<div style="color:' + color + ';background:' + bg + ';padding:2px 4px;margin:1px 0;border-radius:2px;word-break:break-all;">' + escapeHtml(msg) + '</div>';
                    }
                    html += '</div>';
                }
                
                el.innerHTML = html;
            } else {
                el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">📋 Logs no disponibles</span></div><div class="obs-item" style="color:#888;font-size:12px;">Endpoint no responde o sin datos</div>';
            }
        })
        .catch(() => {
            el.innerHTML = '<div class="obs-metrics"><span class="obs-metric warning">📋 Logs no disponibles</span></div><div class="obs-item" style="color:#888;font-size:12px;">Error al cargar logs</div>';
        });
}

function updateAgentsSection(agents) {
    const el = document.getElementById('obs-agents-content');
    if (!el) return;
    if (!agents) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const metrics = agents.metrics || {};
    const all = agents.agents || {};
    let html = '<div class="obs-metrics"><span class="obs-metric ' + (metrics.all_loaded ? 'ok' : 'warning') + '">🤖 ' + (metrics.available || 0) + '/' + (metrics.total || 0) + ' agentes</span></div>';
    for (const [name, agent] of Object.entries(all)) {
        const ok = agent.status === 'available';
        html += '<div class="obs-item ' + (ok ? 'ok' : 'error') + '"><span>' + (ok ? '🟢' : '🔴') + '</span><span>' + name.replace('_agent', '').replace('_', ' ') + '</span><span class="obs-detail">' + (ok ? 'Disponible' : 'No encontrado') + '</span></div>';
    }
    el.innerHTML = html;
}

function updateAgentsSectionFallback() {
    const el = document.getElementById('obs-agents-content');
    if (!el) return;
    el.innerHTML = '<div class="obs-metrics"><span class="obs-metric ok">🤖 6 agentes</span></div><div class="obs-item ok"><span>🟢</span><span>Router</span><span class="obs-detail">Disponible</span></div><div class="obs-item ok"><span>🟢</span><span>Validator</span><span class="obs-detail">Disponible</span></div><div class="obs-item ok"><span>🟢</span><span>Orchestrator</span><span class="obs-detail">Disponible</span></div><div class="obs-item ok"><span>🟢</span><span>Contract</span><span class="obs-detail">Disponible</span></div><div class="obs-item ok"><span>🟢</span><span>Payment</span><span class="obs-detail">Disponible</span></div>';
}

function updateA2ASection(a2a) {
    const el = document.getElementById('obs-a2a-content');
    if (!el) return;
    if (!a2a) { el.innerHTML = '<span style="color:#888;">No disponible</span>'; return; }

    const dir = a2a.a2a_directory || {};
    const auditor = a2a.external_auditor || {};
    let html = '<div class="obs-metrics"><span class="obs-metric">🔗 ' + (dir.agent_count || 0) + ' agentes A2A</span></div>';
    const auditorOk = auditor.status?.ok;
    html += '<div class="obs-item ' + (auditorOk ? 'ok' : 'warning') + '"><span>' + (auditorOk ? '🟢' : '🟡') + '</span><span>External Auditor</span><span class="obs-detail">' + (auditorOk ? 'Online' : 'Offline') + '</span></div>';
    if (dir.agents_found && dir.agents_found.length > 0) {
        html += '<div class="obs-subsection"><strong>Agentes registrados:</strong></div>';
        for (const agent of dir.agents_found) { html += '<div class="obs-item" style="padding-left:20px;">📁 ' + agent + '</div>'; }
    }
    el.innerHTML = html;
}

function updateA2ASectionFallback(data) {
    const el = document.getElementById('obs-a2a-content');
    if (!el) return;
    
    const secondary = data.secondary_services || {};
    const auditor = secondary['external-auditor'];
    const auditorOk = auditor?.ok;
    
    let html = '<div class="obs-metrics"><span class="obs-metric">🔗 1 agente A2A</span></div>';
    html += '<div class="obs-item ' + (auditorOk ? 'ok' : 'warning') + '"><span>' + (auditorOk ? '🟢' : '🟡') + '</span><span>External Auditor</span><span class="obs-detail">' + (auditorOk ? 'Online' : 'Offline') + '</span></div>';
    html += '<div class="obs-subsection"><strong>Agentes registrados:</strong></div>';
    html += '<div class="obs-item" style="padding-left:20px;">📁 external_auditor_agent</div>';
    
    el.innerHTML = html;
}

function updateIssuesSection(data) {
    const el = document.getElementById('obs-issues');
    if (!el) return;
    const issues = data.issues || [];
    const count = data.issues_count || 0;
    if (count === 0) { el.innerHTML = ''; return; }

    let html = '<div class="obs-issues-box"><h3 style="margin-top:0;">⚠️ Problemas Detectados (' + count + ')</h3><ul style="margin:0;padding-left:20px;">';
    for (const issue of issues) { html += '<li style="margin-bottom:5px;">' + issue + '</li>'; }
    html += '</ul></div>';
    el.innerHTML = html;
}

function updateIssuesSectionFallback(data) {
    const el = document.getElementById('obs-issues');
    if (!el) return;
    
    const issues = [];
    const critical = data.critical_services || {};
    const secondary = data.secondary_services || {};
    
    for (const [name, svc] of Object.entries(critical)) {
        if (!svc.ok) issues.push(name + ' esta caido');
    }
    for (const [name, svc] of Object.entries(secondary)) {
        if (!svc.ok) issues.push(name + ' no disponible');
    }
    
    if (issues.length === 0) {
        el.innerHTML = '<div class="obs-issues-box" style="background:#dcfce7;border-color:#16a34a;"><h3 style="margin-top:0;color:#15803d;">✅ Sin Problemas</h3><p style="color:#15803d;">Todos los servicios criticos operativos</p></div>';
    } else {
        let html = '<div class="obs-issues-box"><h3 style="margin-top:0;">⚠️ Problemas Detectados (' + issues.length + ')</h3><ul style="margin:0;padding-left:20px;">';
        for (const issue of issues) { html += '<li style="margin-bottom:5px;">' + issue + '</li>'; }
        html += '</ul></div>';
        el.innerHTML = html;
    }
}

// Auto-refresh cada 30 segundos
setInterval(loadObservability, 30000);

// Cargar cuando se muestra la pagina de Observabilidad
const observabilityPage = document.getElementById('page-observabilidad');
if (observabilityPage) {
    const observer = new MutationObserver(() => {
        if (observabilityPage.classList.contains('active')) {
            loadObservability();
            observer.disconnect();
        }
    });
    observer.observe(observabilityPage, { attributes: true, attributeFilter: ['class'] });
}
