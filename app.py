from pathlib import Path
import runpy

runpy.run_path(Path(__file__).resolve().parent / "src" / "app.py", run_name="__main__")
