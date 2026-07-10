import sys
sys.path.insert(0, r"c:\Users\gisel\OneDrive\Escritorio\tp_multiagentes\invoice_approval_system")

try:
    import app.backend.main
    print("OK - Backend imports successfully")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
