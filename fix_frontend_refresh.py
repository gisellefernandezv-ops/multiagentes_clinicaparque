"""Add auto-refresh to frontend."""
from pathlib import Path

content = Path('app/frontend/app.js').read_text(encoding='utf-8')

# Add auto-refresh for inbox and dashboard after loadDashboard
old_code = '''// Refrescar health cada 30 segundos
setInterval(checkAgentsHealth, 30000);'''

new_code = '''// Refrescar health cada 30 segundos
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
}, 10000);'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("Auto-refresh agregado")
else:
    print("No se encontro el codigo")

Path('app/frontend/app.js').write_text(content, encoding='utf-8')
print("Archivo guardado")
