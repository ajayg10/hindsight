import ast
from pathlib import Path

def test_baseline_independence():
    root = Path(__file__).resolve().parents[1]
    baseline_file = root / "backend" / "app" / "baseline.py"
    assert baseline_file.exists(), f"baseline.py not found at {baseline_file}"
    
    code = baseline_file.read_text(encoding="utf-8")
    tree = ast.parse(code)
    
    forbidden = {"falkordb", "redis", "psycopg2", "sqlite3", "app.mcp_server", "backend.app.mcp_server"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                assert n.name not in forbidden, f"Forbidden import in baseline.py: {n.name}"
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden, f"Forbidden import from in baseline.py: {node.module}"
            
    print("✓ PASS: baseline.py has ZERO DB client imports (strict AST independence).")

if __name__ == "__main__":
    test_baseline_independence()
