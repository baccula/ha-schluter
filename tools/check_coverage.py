"""Enforce Silver's per-module coverage and complete config-flow coverage."""

import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text())
failed = []
for name, data in report["files"].items():
    summary = data["summary"]
    total = summary["num_statements"]
    covered = summary["covered_lines"]
    ratio = 100 * covered / total if total else 100
    if ratio <= 95 or (name.endswith("config_flow.py") and covered != total):
        failed.append(f"{name}: {ratio:.2f}%")
if failed:
    raise SystemExit("Coverage requirement failed:\n" + "\n".join(failed))
print("Every measured module exceeds 95%; config flow has complete line coverage.")
