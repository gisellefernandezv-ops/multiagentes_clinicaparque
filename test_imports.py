import sys
sys.path.insert(0, '.')
try:
    import app.services.contract_service.main
    print("Contract service imports OK")
except Exception as e:
    print(f"Contract service ERROR: {e}")
