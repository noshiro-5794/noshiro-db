"""Compare the Django service and the replacement field by field.

Run it against both services while they share a database:

    uv run python scripts/parity.py \
        --old http://127.0.0.1:8008 --new http://127.0.0.1:8010 \
        --path /api/v1/index/entities/93509ec8-3194-41de-9353-64a9f5f85fbb/metrics/

Exit code 1 means at least one endpoint differs, which is the gate for moving
traffic. The diff is structural: dict keys are compared as sets, list order is
significant, and numeric types are compared by value.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections.abc import Iterator
from typing import Any

DEFAULT_HEADERS = {"Accept": "application/json", "X-Forwarded-Proto": "https"}


def fetch(base_url: str, path: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(base_url.rstrip("/") + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def diff(expected: Any, actual: Any, path: str = "") -> Iterator[str]:
    if _is_number(expected) and _is_number(actual):
        if expected != actual:
            yield f"{path}: {expected!r} != {actual!r}"
        return
    if type(expected) is not type(actual):
        yield f"{path}: type {type(expected).__name__} != {type(actual).__name__}"
        return
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                yield f"{path}.{key}: missing in the new response"
            elif key not in expected:
                yield f"{path}.{key}: extra in the new response"
            else:
                yield from diff(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            yield f"{path}: length {len(expected)} != {len(actual)}"
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            yield from diff(left, right, f"{path}[{index}]")
        return
    if expected != actual:
        yield f"{path}: {expected!r} != {actual!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="Django base URL")
    parser.add_argument("--new", required=True, help="replacement base URL")
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--header", action="append", default=[], metavar="KEY: VALUE")
    args = parser.parse_args(argv)

    headers = dict(DEFAULT_HEADERS)
    for header in args.header:
        key, _, value = header.partition(":")
        headers[key.strip()] = value.strip()

    failures = 0
    for path in args.path:
        try:
            expected = fetch(args.old, path, headers)
            actual = fetch(args.new, path, headers)
        except Exception as error:
            print(f"FAIL {path}: {error}")
            failures += 1
            continue
        differences = list(diff(expected, actual))
        if differences:
            failures += 1
            print(f"FAIL {path}")
            for line in differences[:20]:
                print(f"  {line}")
        else:
            print(f"OK   {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
