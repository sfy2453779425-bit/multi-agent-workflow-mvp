"""Resume the interrupted Claude formal run of ac_formal_v2.

The first `run_claude_cli.py --formal` run was interrupted by the operator after 13/18 calls.
Every completed call had its output file and a log line with matching sha256; there were no
partial artifacts. This wrapper runs only the scheduled calls that have no output file, through
the frozen runner unchanged (same call path, isolation, retry rules, log format and freeze
check). Completed calls are never re-run or overwritten.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_claude_cli as r  # noqa: E402

config, calls = r.load_plan()
out_dir = r.EXP_DIR / "cli_raw" / config["experiment_id"] / r.PROVIDER_KEY
missing = [c for c in calls if not (out_dir / f"{c['case_id']}_run{c['run_id']}.json").exists()]
print("resuming:", " ".join(f"#{c['schedule_index']}:{c['case_id']}/r{c['run_id']}" for c in missing))
if missing:
    r.do_formal(r.claude_exe(), config, missing)
