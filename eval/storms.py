"""
Proxy to backend/eval/storms.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from eval.storms import run_suite

if __name__ == "__main__":
    run_suite()
