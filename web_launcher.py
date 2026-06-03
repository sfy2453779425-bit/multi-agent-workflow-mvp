import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "outputs"
LOG_DIR.mkdir(exist_ok=True)

sys.stdout = (LOG_DIR / "web_server_stdout.log").open("a", encoding="utf-8", buffering=1)
sys.stderr = (LOG_DIR / "web_server_stderr.log").open("a", encoding="utf-8", buffering=1)
sys.argv = [str(ROOT / "web_app.py"), *(sys.argv[1:] or ["8000"])]
runpy.run_path(str(ROOT / "web_app.py"), run_name="__main__")
