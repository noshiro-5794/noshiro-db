"""Export the OpenAPI document from the application route definitions."""

import json
from pathlib import Path

from api.main import create_app


def main() -> None:
    target = Path(__file__).resolve().parents[2] / "tests/snapshots/openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
