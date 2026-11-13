"""How much of the Celery surface the replacement has taken over.

Static on purpose: it reads the Django task definitions and the task names the worker
registers, without importing either project. That keeps it runnable from any checkout,
including one whose virtualenv does not have Django installed.

    python scripts/task_coverage.py [--json]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DJANGO_TASKS = REPO / "apps/api/src/apps"
WORKER = REPO / "apps/api-v2/src/api/worker"

TASK_DEF = re.compile(r"@shared_task[^\n]*\n(?:@[^\n]*\n)*def\s+(\w+)\s*\(")
REGISTERED = re.compile(r'(?<![\w.])name="([\w.]+)"')

# Names the worker registers that are deliberately not Django task names (a probe or a
# local helper). Keep this empty unless there is a reason; it exists so the check can
# stay strict.
IGNORED_NAMES: set[str] = set()


def django_tasks() -> dict[str, str]:
    """Task function name -> the module path it lives in."""
    found: dict[str, str] = {}
    for path in sorted(DJANGO_TASKS.rglob("*.py")):
        if "tasks" not in path.parts and path.name != "tasks.py":
            continue
        text = path.read_text()
        if "@shared_task" not in text:
            continue
        relative = path.relative_to(REPO / "apps/api/src").with_suffix("")
        module = ".".join(relative.parts)
        for name in TASK_DEF.findall(text):
            found[name] = module
    return found


def registered_names() -> set[str]:
    """The Django-style names the replacement registers."""
    names: set[str] = set()
    for path in sorted(WORKER.rglob("*.py")):
        names.update(REGISTERED.findall(path.read_text()))
    return names


def coverage() -> dict[str, list[str] | float]:
    tasks = django_tasks()
    known = {f"{module}.{name}" for name, module in tasks.items()}
    taken = registered_names()
    done = sorted(name for name, module in tasks.items() if f"{module}.{name}" in taken)
    missing = sorted(name for name, module in tasks.items() if f"{module}.{name}" not in taken)
    # A name registered here that Django does not define is almost certainly a typo,
    # and a typo'd task is never consumed: the message sits on the queue and nothing
    # reports it. Surfacing the set is the cheapest way to catch that.
    unknown = sorted(taken - known - IGNORED_NAMES)
    return {
        "total": len(tasks),
        "taken": len(done),
        "percent": round(100 * len(done) / len(tasks), 1) if tasks else 0.0,
        "done": done,
        "missing": missing,
        "unknown": unknown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    result = coverage()
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"worker coverage: {result['taken']}/{result['total']} ({result['percent']}%)")
    print("done:")
    for name in result["done"]:
        print(f"  + {name}")
    print("missing:")
    for name in result["missing"]:
        print(f"  - {name}")
    if result["unknown"]:
        print("registered but unknown to Django (typo?):")
        for name in result["unknown"]:
            print(f"  ! {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
