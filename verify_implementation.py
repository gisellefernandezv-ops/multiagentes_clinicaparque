"""Script de verificación de implementación — InvoiceFlow."""

import sys
sys.path.insert(0, '.')

def test_imports():
    print("=" * 60)
    print("VERIFICACIÓN DE IMPLEMENTACIÓN")
    print("=" * 60)
    
    errors = []
    
    # Test 1: Guardrail Engine
    print("\n1. Guardrail Engine...")
    try:
        from guardrails.guardrail_engine import GuardrailEngine, evaluate_guardrails
        engine = GuardrailEngine()
        print(f"   ✓ {len(engine._rules)} reglas cargadas")
        print(f"   ✓ Constantes: {list(engine._constantes.keys())}")
    except Exception as e:
        errors.append(f"guardrail_engine: {e}")
        print(f"   ✗ Error: {e}")
    
    # Test 2: Router Agent
    print("\n2. Router Agent...")
    try:
        from agents.router_agent import create_router_agent, classify_intention_tool
        agent = create_router_agent()
        print(f"   ✓ Agente creado: {agent.name}")
        
        # Test de clasificación
        r = classify_intention_tool("Quiero subir una factura")
        print(f"   ✓ Clasificación: {r['intention']}")
    except Exception as e:
        errors.append(f"router_agent: {e}")
        print(f"   ✗ Error: {e}")
    
    # Test 3: Invoice Status Tool
    print("\n3. Invoice Status Tool...")
    try:
        from tools.invoice_status_tool import (
            check_invoice_status_tool,
            list_supplier_invoices_tool,
            get_supplier_status_summary_tool
        )
        print("   ✓ Tools importadas")
        
        # Test de consulta
        r = check_invoice_status_tool("INV-TEST", "SUP001")
        print(f"   ✓ Consulta: found={r['found']}")
    except Exception as e:
        errors.append(f"invoice_status_tool: {e}")
        print(f"   ✗ Error: {e}")
    
    # Test 4: ML Risk Tool
    print("\n4. ML Risk Tool...")
    try:
        from tools.ml_risk_tool import evaluate_risk_tool
        r = evaluate_risk_tool("SUP001", 50000, "2025-06-01")
        print(f"   ✓ Evaluación: {r['risk_level']} (score: {r['risk_score']})")
    except Exception as e:
        errors.append(f"ml_risk_tool: {e}")
        print(f"   ✗ Error: {e}")
    
    # Test 5: External Auditor
    print("\n5. External Auditor Agent...")
    try:
        from a2a.external_auditor_agent.agent import (
            create_external_auditor_agent,
            perform_audit_tool
        )
        agent = create_external_auditor_agent()
        print(f"   ✓ Agente creado: {agent.name}")
        
        r = perform_audit_tool("FC-001", "SUP001", 750000)
        print(f"   ✓ Auditoría: {r['audit_result']}")
    except Exception as e:
        errors.append(f"external_auditor_agent: {e}")
        print(f"   ✗ Error: {e}")
    
    # Test 6: Files existence
    print("\n6. Verificación de archivos...")
    from pathlib import Path
    
    files_to_check = [
        "guardrails/rules.yaml",
        "guardrails/guardrail_engine.py",
        "agents/router_agent.py",
        "tools/invoice_status_tool.py",
        "tools/ml_risk_tool.py",
        "a2a/external_auditor_agent/agent.py",
        "a2a/external_auditor_agent/server.py",
        "tests/eval/datasets/invoiceflow-dataset.json",
        "tests/eval/eval_config.yaml",
        "supplier_portal/index.html",
        "supplier_portal/style.css",
        "platform/frontend/index.html",
        "platform/frontend/style.css",
        "platform/frontend/app.js",
    ]
    
    for f in files_to_check:
        if Path(f).exists():
            print(f"   ✓ {f}")
        else:
            errors.append(f"Missing: {f}")
            print(f"   ✗ {f} (FALTA)")
    
    # Test 7: Rules
    print("\n7. Verificación de reglas...")
    try:
        from guardrails.guardrail_engine import GuardrailEngine
        engine = GuardrailEngine()
        
        required_rules = [
            "VR-01", "VR-02", "VR-03", "VR-04", "VR-05", "VR-06", "VR-07",
            "BR-01", "BR-02", "BR-03", "BR-04", "BR-05", "BR-06", "BR-07", "BR-08", "BR-09", "BR-10",
            "SR-01", "SR-02", "SR-03", "SR-04", "SR-05",
            "CR-01", "CR-02", "CR-03"
        ]
        
        for rule_id in required_rules:
            rule = engine.get_rule(rule_id)
            if rule:
                print(f"   ✓ {rule_id}: {rule['tipo']} - {rule['accion']}")
            else:
                errors.append(f"Missing rule: {rule_id}")
                print(f"   ✗ {rule_id} (FALTA)")
    except Exception as e:
        print(f"   ✗ Error verificando reglas: {e}")
    
    # Resumen
    print("\n" + "=" * 60)
    if errors:
        print(f"RESULTADO: {len(errors)} error(es) encontrado(s)")
        for e in errors:
            print(f"  - {e}")
    else:
        print("RESULTADO: ✓ TODOS LOS COMPONENTES VERIFICADOS")
    print("=" * 60)
    
    return len(errors) == 0


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
