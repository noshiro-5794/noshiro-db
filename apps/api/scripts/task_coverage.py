"""Verify worker registrations against the retained broker task contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WORKER = REPO / "apps/api/src/api/worker"
INVENTORY = Path(__file__).with_name("task_inventory.json")
REGISTERED = re.compile(r'(?<![\w.])name="([\w.]+)"')
MIN_REGISTERED = 30


def contract_tasks() -> dict[str, str]:
    """Read the retained broker-message task contract."""
    names = json.loads(INVENTORY.read_text())
    return {name.rsplit(".", 1)[1]: name.rsplit(".", 1)[0] for name in names}


def registered_names() -> set[str]:
    """The names registered by the worker."""
    names: set[str] = set()
    for path in sorted(WORKER.rglob("*.py")):
        names.update(REGISTERED.findall(path.read_text()))
    return names


def coverage() -> dict[str, list[str] | float]:
    tasks = contract_tasks()
    known = {f"{module}.{name}" for name, module in tasks.items()}
    taken = registered_names()
    done = sorted(name for name, module in tasks.items() if f"{module}.{name}" in taken)
    missing = sorted(name for name, module in tasks.items() if f"{module}.{name}" not in taken)
    # Detect typos before messages are published under an unconsumed task name.
    unknown = sorted(taken - known)
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
    if result["taken"] < MIN_REGISTERED:
        print(
            f"REGRESSION: {result['taken']} registered tasks, floor is {MIN_REGISTERED}"
            " — a registration was probably removed"
        )
        return 1
    if result["unknown"]:
        print("registered outside the broker task contract:")
        for name in result["unknown"]:
            print(f"  ! {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
