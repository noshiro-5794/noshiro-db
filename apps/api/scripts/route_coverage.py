"""Compare registered HTTP operations with the retained public API contract."""

import json
import re
from pathlib import Path
from typing import Any

from api.main import create_app

INVENTORY = Path(__file__).with_name("route_inventory.json")


def normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def coverage() -> dict[str, Any]:
    required = {
        (method, normalize(row["path"]))
        for row in json.loads(INVENTORY.read_text())
        for method in row["methods"]
    }
    app = create_app()
    registered = {
        (method.upper(), normalize(path))
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete", "head", "options"}
    }
    registered.update(
        {
            (method, normalize(route.path))
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
        }
    )
    missing = sorted(required - registered)
    return {
        "required": len(required),
        "registered": len(required & registered),
        "missing": [f"{method} {path}" for method, path in missing],
    }


def main() -> int:
    result = coverage()
    print(f"HTTP operation coverage {result['registered']}/{result['required']}")
    for operation in result["missing"]:
        print(f"  {operation}")
    return int(bool(result["missing"]))


if __name__ == "__main__":
    raise SystemExit(main())
