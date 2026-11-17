"""Compare ruff and mypy findings against a recorded baseline. New findings fail; existing ones are tracked, not hidden.

    python tools/lint_baseline.py check ruff
    python tools/lint_baseline.py check mypy
    python tools/lint_baseline.py write          # regenerate tools/lint_baseline.json (a reviewed change, not a CI step)

A finding is counted per file and rule code, not per line, so editing a file does not change its count unless a finding
is added or removed. A count above its baseline, or a (file, rule) pair that is not in the baseline, fails. A count
below it passes and says so, so the baseline can be tightened. Nothing here suppresses a finding in the source."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASELINE = Path(__file__).with_name("lint_baseline.json")
ROOT = Path(__file__).resolve().parents[1]
_MYPY_LINE = re.compile(r"^(?P<path>[^:\n]+):\d+: error: .*\[(?P<code>[a-z0-9-]+)\]\s*$")


def ruff_counts(output_json: str) -> Counter:
    counts: Counter = Counter()
    for item in json.loads(output_json):
        path = str(Path(item["filename"]).resolve().relative_to(ROOT)).replace("\\", "/")
        counts[f"{path}::{item['code']}"] += 1
    return counts


def mypy_counts(output_text: str) -> Counter:
    counts: Counter = Counter()
    for line in output_text.splitlines():
        match = _MYPY_LINE.match(line)
        if match:
            counts[f"{match['path'].replace(chr(92), '/')}::{match['code']}"] += 1
    return counts


def compare(found: Counter, baseline: dict) -> tuple[list[str], list[str]]:
    """(failures, improvements). A failure is a count above its baseline or a pair the baseline does not know."""
    failures, improvements = [], []
    for key, count in sorted(found.items()):
        allowed = baseline.get(key, 0)
        if count > allowed:
            failures.append(f"{key}: {count} found, baseline allows {allowed}")
    for key, allowed in sorted(baseline.items()):
        if found.get(key, 0) < allowed:
            improvements.append(f"{key}: {found.get(key, 0)} found, baseline has {allowed}; tighten it")
    return failures, improvements


def _run(tool: str) -> Counter:
    if tool == "ruff":
        out = subprocess.run([sys.executable, "-m", "ruff", "check", ".", "--output-format", "json"],
                             cwd=ROOT, capture_output=True, text=True, check=False)
        return ruff_counts(out.stdout or "[]")
    if tool == "mypy":
        out = subprocess.run([sys.executable, "-m", "mypy", "src"], cwd=ROOT, capture_output=True, text=True, check=False)
        return mypy_counts(out.stdout)
    raise SystemExit(f"unknown tool {tool!r}")


def main(argv: list[str]) -> int:
    if len(argv) == 1 and argv[0] == "write":
        data = {tool: dict(sorted(_run(tool).items())) for tool in ("ruff", "mypy")}
        BASELINE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print(f"wrote {BASELINE.name}: " + ", ".join(f"{t} {sum(v.values())}" for t, v in data.items()))
        return 0
    if len(argv) == 2 and argv[0] == "check":
        tool = argv[1]
        failures, improvements = compare(_run(tool), json.loads(BASELINE.read_text()).get(tool, {}))
        for line in improvements:
            print(f"improved  {line}")
        for line in failures:
            print(f"NEW       {line}")
        print(f"{tool}: {'FAIL, new findings' if failures else 'ok, nothing above the baseline'}")
        return 1 if failures else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
