"""Extended Health Check and Observability Module.

This module provides comprehensive health checking for all system components.
Version: 3.0.1 - Robust with error handling
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import os
import sqlite3
import httpx
import json
import yaml
import re
from collections import defaultdict


# ============================================================================
# SERVICE HEALTH CHECKS
# ============================================================================

async def check_service(name: str, url: str, timeout: float = 3.0) -> Dict[str, Any]:
    """Checks a single service health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{url}/health", timeout=timeout)
            if r.status_code == 200:
                return {
                    "ok": True,
                    "status": "up",
                    "details": r.json(),
                    "response_time_ms": r.elapsed.total_seconds() * 1000
                }
            return {"ok": False, "status": f"error_{r.status_code}"}
    except httpx.ConnectError:
        return {"ok": False, "status": "connection_error"}
    except httpx.TimeoutException:
        return {"ok": False, "status": "timeout"}
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


async def check_all_services(settings: Any, project_root: Path) -> Dict[str, Any]:
    """Checks health of all services in the system."""
    services = {}
    
    critical = [
        ("backend", f"http://127.0.0.1:{settings.port}"),
        ("supplier_service", f"{settings.supplier_service_url}"),
        ("contract_service", f"{settings.contract_service_url}"),
    ]
    
    secondary = [
        ("mcp_toolbox", "http://127.0.0.1:5000"),
        ("external_auditor_a2a", "http://127.0.0.1:8003"),
    ]
    
    try:
        for name, url in critical:
            services[name] = {
                "url": f"{url}/health",
                "type": "critical",
                "status": await check_service(name, url)
            }
        
        for name, url in secondary:
            services[name] = {
                "url": f"{url}/health",
                "type": "secondary",
                "status": await check_service(name, url, timeout=2.0)
            }
    except Exception as e:
        return {
            "services": {},
            "metrics": {"error": str(e), "total": 0, "up": 0}
        }
    
    up_count = sum(1 for s in services.values() if s["status"].get("ok", False))
    critical_ok = all(
        s["type"] == "critical" and s["status"].get("ok", False) 
        for s in services.values()
    )
    
    return {
        "services": services,
        "metrics": {
            "total": len(services),
            "up": up_count,
            "down": len(services) - up_count,
            "all_critical_healthy": critical_ok,
            "all_services_healthy": all(s["status"].get("ok", False) for s in services.values())
        }
    }


# ============================================================================
# DATABASE HEALTH CHECKS
# ============================================================================

def check_database(db_path: Path) -> Dict[str, Any]:
    """Checks SQLite database connectivity and basic stats."""
    if not db_path.exists():
        return {"ok": False, "status": "not_found", "path": str(db_path), "tables": []}
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except:
                pass
        
        file_size = os.path.getsize(db_path)
        conn.close()
        
        return {
            "ok": True,
            "status": "ok",
            "path": str(db_path),
            "tables": tables,
            "table_count": len(tables),
            "counts": counts,
            "total_rows": sum(counts.values()),
            "size_bytes": file_size,
            "size_human": _human_readable_size(file_size)
        }
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


async def check_all_databases(settings: Any, project_root: Path) -> Dict[str, Any]:
    """Checks all SQLite databases in the system."""
    databases = {
        "suppliers_db": settings.data_dir / "suppliers.db",
        "payments_db": project_root / "data" / "payments.db",
        "chat_sessions_db": project_root / "data" / "chat_sessions.db",
        "inbox_db": project_root / "data" / "inbox.db"
    }
    
    results = {}
    try:
        for name, path in databases.items():
            results[name] = check_database(path)
    except Exception as e:
        return {"databases": {}, "metrics": {"error": str(e), "total": 0, "ok": 0}}
    
    all_ok = all(d.get("ok", False) for d in results.values())
    
    return {
        "databases": results,
        "metrics": {
            "total": len(databases),
            "ok": sum(1 for d in results.values() if d.get("ok", False)),
            "failed": sum(1 for d in results.values() if not d.get("ok", False)),
            "all_healthy": all_ok
        }
    }


# ============================================================================
# MCP INTEGRATION CHECKS
# ============================================================================

async def check_mcp_toolbox_server(project_root: Path) -> Dict[str, Any]:
    """Checks MCP Toolbox server status and configuration."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://127.0.0.1:5000/health")
            if r.status_code == 200:
                return {"ok": True, "status": "running", "port": 5000}
    except:
        pass
    
    mcp_config_path = project_root / "mcp_config" / "tools.yaml"
    mcp_servers_path = project_root / "mcp_config" / "mcp_servers.json"
    
    mcp_tools = []
    mcp_servers = []
    
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                for t in config.get("tools", []):
                    mcp_tools.append({"name": t.get("name"), "description": t.get("description", "")[:50]})
        except:
            pass
    
    if mcp_servers_path.exists():
        try:
            with open(mcp_servers_path, "r", encoding="utf-8") as f:
                servers_config = json.load(f)
                for name, info in servers_config.get("mcpServers", {}).items():
                    mcp_servers.append({"name": name, "command": info.get("command")})
        except:
            pass
    
    return {
        "ok": True,
        "status": "not_running",
        "config_exists": mcp_config_path.exists(),
        "config_path": str(mcp_config_path),
        "servers_config_exists": mcp_servers_path.exists(),
        "configured_tools": mcp_tools,
        "tools_count": len(mcp_tools),
        "mcp_servers": mcp_servers,
        "servers_count": len(mcp_servers),
        "start_command": "python -m app.services.toolbox_server.main"
    }


async def check_mcp_integrations(project_root: Path) -> Dict[str, Any]:
    """Comprehensive MCP integration check."""
    try:
        toolbox_status = await check_mcp_toolbox_server(project_root)
        return {
            "mcp_toolbox": toolbox_status,
            "integration_summary": {
                "server_available": toolbox_status.get("status") == "running",
                "tools_configured": toolbox_status.get("tools_count", 0),
                "servers_configured": toolbox_status.get("servers_count", 0),
                "configuration_valid": toolbox_status.get("config_exists", False)
            }
        }
    except Exception as e:
        return {
            "mcp_toolbox": {"ok": False, "error": str(e)},
            "integration_summary": {"server_available": False}
        }


# ============================================================================
# RAG / CHROMADB CHECKS
# ============================================================================

def check_rag_index(rag_dir: Path) -> Dict[str, Any]:
    """Checks RAG/ChromaDB index status."""
    if not rag_dir.exists():
        return {"ok": False, "status": "not_initialized", "path": str(rag_dir), "collections": []}
    
    try:
        collections = list(rag_dir.iterdir()) if rag_dir.is_dir() else []
        total_docs = 0
        collection_details = []
        
        chroma_sqlite = rag_dir / "chroma.sqlite3"
        if chroma_sqlite.exists():
            try:
                conn = sqlite3.connect(str(chroma_sqlite))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM collections")
                cursor.execute("SELECT id, name FROM collections")
                collection_details = [{"id": str(row[0]), "name": row[1]} for row in cursor.fetchall()]
                try:
                    cursor.execute("SELECT COUNT(*) FROM embeddings")
                    total_docs = cursor.fetchone()[0]
                except:
                    pass
                conn.close()
            except:
                pass
        
        return {
            "ok": True,
            "status": "ready",
            "path": str(rag_dir),
            "collections_count": len(collections),
            "collections": collection_details,
            "total_documents": total_docs
        }
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


async def check_rag_integration(settings: Any, project_root: Path) -> Dict[str, Any]:
    """Checks RAG/ChromaDB integration status."""
    try:
        rag_index = check_rag_index(settings.data_dir / "chroma_db")
        rag_backup = check_rag_index(project_root / "data" / "chroma_db")
        
        return {
            "primary_rag": rag_index,
            "backup_rag": rag_backup,
            "integration_status": {
                "primary_available": rag_index.get("ok", False),
                "backup_available": rag_backup.get("ok", False),
                "documents_indexed": rag_index.get("total_documents", 0)
            }
        }
    except Exception as e:
        return {
            "primary_rag": {"ok": False, "error": str(e)},
            "backup_rag": {"ok": False},
            "integration_status": {"documents_indexed": 0}
        }


# ============================================================================
# FILE SYSTEM MONITORING
# ============================================================================

def get_file_stats(directory: Path, extensions: List[str] = None) -> Dict[str, Any]:
    """Gets detailed file count and size statistics for a directory."""
    if not directory.exists():
        return {"ok": False, "status": "not_found"}
    
    try:
        files = list(directory.rglob("*")) if directory.is_dir() else []
        all_files = [f for f in files if f.is_file()]
        
        if extensions:
            all_files = [f for f in all_files if f.suffix.lower() in extensions]
        
        total_size = sum(f.stat().st_size for f in all_files)
        
        return {
            "ok": True,
            "path": str(directory),
            "file_count": len(all_files),
            "size_bytes": total_size,
            "size_human": _human_readable_size(total_size)
        }
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


async def check_file_system(settings: Any, project_root: Path) -> Dict[str, Any]:
    """Checks all monitored file system paths."""
    paths = {
        "inbox": settings.inbox_dir,
        "processed": settings.processed_dir,
        "rejected": settings.rejected_dir,
        "new_invoices": project_root / "data" / "new invoices",
        "contracts": project_root / "data" / "contracts"
    }
    
    stats = {}
    try:
        for name, path in paths.items():
            stats[name] = get_file_stats(path)
    except Exception as e:
        return {"paths": {}, "metrics": {"error": str(e)}}
    
    total_files = sum(s.get("file_count", 0) for s in stats.values())
    total_size = sum(s.get("size_bytes", 0) for s in stats.values())
    
    return {
        "paths": stats,
        "watcher_enabled": settings.enable_watcher,
        "watched_directory": str(settings.inbox_dir) if settings.enable_watcher else None,
        "metrics": {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_human": _human_readable_size(total_size),
            "paths_monitored": len(paths)
        }
    }


# ============================================================================
# LOG TRACKING
# ============================================================================

def get_recent_logs(project_root: Path, lines: int = 100) -> Dict[str, Any]:
    """Gets recent log entries with detailed analysis."""
    log_file = project_root / "data" / "logs" / "invoiceflow.log"
    
    if not log_file.exists():
        return {"ok": False, "status": "no_log_file", "path": str(log_file)}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        level_counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "DEBUG": 0}
        entries_with_level = []
        
        for line in recent:
            stripped = line.strip()
            if not stripped:
                continue
            
            level = "INFO"
            if "] INFO:" in stripped: level = "INFO"
            elif "] WARNING:" in stripped: level = "WARNING"
            elif "] ERROR:" in stripped: level = "ERROR"
            elif "] DEBUG:" in stripped: level = "DEBUG"
            
            level_counts[level] += 1
            entries_with_level.append({"level": level, "message": stripped})
        
        return {
            "ok": True,
            "path": str(log_file),
            "total_lines": len(all_lines),
            "recent_lines": len(recent),
            "entries": entries_with_level,
            "level_counts": level_counts,
            "file_size_bytes": os.path.getsize(log_file)
        }
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


def get_logs_by_level(project_root: Path, level: str = "ERROR", max_lines: int = 50) -> Dict[str, Any]:
    """Gets log entries filtered by level."""
    log_file = project_root / "data" / "logs" / "invoiceflow.log"
    
    if not log_file.exists():
        return {"ok": False, "status": "no_log_file"}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        pattern = f"] {level}:"
        filtered = [line.strip() for line in all_lines if pattern in line][-max_lines:]
        
        return {"ok": True, "level": level, "count": len(filtered), "entries": filtered}
    except Exception as e:
        return {"ok": False, "status": "error", "error": str(e)}


async def check_log_system(project_root: Path) -> Dict[str, Any]:
    """Comprehensive log system check."""
    try:
        recent_logs = get_recent_logs(project_root, lines=100)
        error_logs = get_logs_by_level(project_root, "ERROR", max_lines=20)
        warning_logs = get_logs_by_level(project_root, "WARNING", max_lines=20)
        
        return {
            "recent": recent_logs,
            "errors": error_logs,
            "warnings": warning_logs,
            "metrics": {
                "log_file_exists": recent_logs.get("ok", False),
                "total_errors": error_logs.get("count", 0),
                "total_warnings": warning_logs.get("count", 0),
                "has_critical_issues": error_logs.get("count", 0) > 0
            }
        }
    except Exception as e:
        return {
            "recent": {"ok": False},
            "errors": {"ok": False},
            "warnings": {"ok": False},
            "metrics": {"error": str(e)}
        }


# ============================================================================
# A2A INTEGRATION CHECKS
# ============================================================================

async def check_a2a_integration(project_root: Path) -> Dict[str, Any]:
    """Checks A2A (Agent-to-Agent) integration status."""
    try:
        auditor_status = await check_service("external_auditor", "http://127.0.0.1:8003", timeout=2.0)
        
        a2a_dir = project_root / "a2a"
        a2a_agents = []
        if a2a_dir.exists():
            for agent_dir in a2a_dir.iterdir():
                if agent_dir.is_dir() and (agent_dir / "agent.py").exists():
                    a2a_agents.append(agent_dir.name)
        
        return {
            "external_auditor": {"url": "http://127.0.0.1:8003/health", "status": auditor_status},
            "a2a_directory": {
                "exists": a2a_dir.exists(),
                "path": str(a2a_dir),
                "agents_found": a2a_agents,
                "agent_count": len(a2a_agents)
            },
            "integration_status": {
                "auditor_available": auditor_status.get("ok", False),
                "protocol_active": len(a2a_agents) > 0
            }
        }
    except Exception as e:
        return {
            "external_auditor": {"status": {"ok": False, "error": str(e)}},
            "a2a_directory": {"agents_found": []},
            "integration_status": {}
        }


# ============================================================================
# AGENT STATUS CHECKS
# ============================================================================

async def check_agents(project_root: Path) -> Dict[str, Any]:
    """Checks status of all agents in the system."""
    agents_dir = project_root / "agents"
    agents = {}
    
    if not agents_dir.exists():
        return {"ok": False, "status": "agents_not_found", "path": str(agents_dir)}
    
    agent_files = [
        "router_agent.py", "validator_agent.py", "orchestrator.py",
        "contract_agent.py", "payment_agent.py", "invoice_manager_agent.py"
    ]
    
    try:
        for agent_file in agent_files:
            agent_path = agents_dir / agent_file
            name = agent_file.replace(".py", "")
            agents[name] = {
                "exists": agent_path.exists(),
                "path": str(agent_path),
                "status": "available" if agent_path.exists() else "not_found"
            }
        
        return {
            "ok": True,
            "agents": agents,
            "metrics": {
                "total": len(agent_files),
                "available": sum(1 for a in agents.values() if a["status"] == "available"),
                "all_loaded": all(a["status"] == "available" for a in agents.values())
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "agents": agents}


# ============================================================================
# COMPREHENSIVE OBSERVABILITY
# ============================================================================

async def get_full_observability(settings: Any, project_root: Path) -> Dict[str, Any]:
    """Gathers full system observability data."""
    try:
        # Gather all health data
        services = await check_all_services(settings, project_root)
        databases = await check_all_databases(settings, project_root)
        mcp = await check_mcp_integrations(project_root)
        rag = await check_rag_integration(settings, project_root)
        files = await check_file_system(settings, project_root)
        logs = await check_log_system(project_root)
        a2a = await check_a2a_integration(project_root)
        agents = await check_agents(project_root)
        
        # Calculate health score
        health_score = 100
        issues = []
        
        if services.get("metrics", {}).get("all_critical_healthy"):
            service_pct = services["metrics"]["up"] / services["metrics"]["total"] if services["metrics"].get("total", 0) > 0 else 1
            health_score -= 40 * (1 - service_pct)
            if service_pct < 1:
                issues.append(f"{services['metrics']['down']} servicios caídos")
        
        if databases.get("metrics", {}).get("all_healthy"):
            db_pct = databases["metrics"]["ok"] / databases["metrics"]["total"] if databases["metrics"].get("total", 0) > 0 else 1
            health_score -= 30 * (1 - db_pct)
        
        if logs.get("metrics", {}).get("total_errors", 0) > 0:
            health_score -= 15
            issues.append(f"{logs['metrics']['total_errors']} errores en logs")
        
        if not mcp.get("integration_summary", {}).get("server_available"):
            health_score -= 10
            issues.append("MCP Toolbox no está corriendo")
        
        if not rag.get("integration_status", {}).get("primary_available"):
            health_score -= 5
        
        overall_status = "healthy" if health_score >= 70 else "degraded" if health_score >= 50 else "unhealthy"
        
        return {
            "status": overall_status,
            "health_score": round(max(0, health_score), 1),
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.1",
            "services": services,
            "databases": databases,
            "integrations": {"mcp": mcp, "rag": rag, "a2a": a2a},
            "files": files,
            "logs": logs,
            "agents": agents,
            "summary": {
                "services_up": services.get("metrics", {}).get("up", 0),
                "services_total": services.get("metrics", {}).get("total", 0),
                "services_critical_healthy": services.get("metrics", {}).get("all_critical_healthy", False),
                "databases_ok": databases.get("metrics", {}).get("ok", 0),
                "databases_total": databases.get("metrics", {}).get("total", 0),
                "mcp_tools_configured": mcp.get("integration_summary", {}).get("tools_configured", 0),
                "mcp_server_running": mcp.get("integration_summary", {}).get("server_available", False),
                "rag_documents_indexed": rag.get("integration_status", {}).get("documents_indexed", 0),
                "inbox_count": files.get("paths", {}).get("inbox", {}).get("file_count", 0),
                "processed_count": files.get("paths", {}).get("processed", {}).get("file_count", 0),
                "rejected_count": files.get("paths", {}).get("rejected", {}).get("file_count", 0),
                "log_entries_available": logs.get("recent", {}).get("ok", False),
                "recent_log_lines": logs.get("recent", {}).get("recent_lines", 0),
                "total_errors": logs.get("metrics", {}).get("total_errors", 0),
                "total_warnings": logs.get("metrics", {}).get("total_warnings", 0),
                "a2a_agents_count": a2a.get("a2a_directory", {}).get("agent_count", 0),
                "auditor_available": a2a.get("integration_status", {}).get("auditor_available", False)
            },
            "issues": issues,
            "issues_count": len(issues)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.1",
            "services": {"services": {}, "metrics": {}},
            "databases": {"databases": {}, "metrics": {}},
            "integrations": {"mcp": {}, "rag": {}, "a2a": {}},
            "files": {"paths": {}},
            "logs": {"recent": {}, "metrics": {}},
            "agents": {"agents": {}},
            "summary": {},
            "issues": [f"Error general: {str(e)}"],
            "issues_count": 1
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _human_readable_size(bytes_size: int) -> str:
    """Convert bytes to human readable format."""
    if bytes_size <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"
