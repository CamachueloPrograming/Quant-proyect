from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))
runpy.run_path(root / "src" / "app.py", run_name="__main__")
