"""OpenAPI error definitions reflecting application exception handlers."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


class ProblemDocument(BaseModel):
    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str
    trace_id: str
    code: str | None = None
    errors: dict[str, list[str]] | None = None


class Application(FastAPI):
    def openapi(self) -> dict[str, Any]:
        schema = super().openapi()
        schema.setdefault("components", {}).setdefault("schemas", {})["ProblemDocument"] = (
            ProblemDocument.model_json_schema()
        )
        response = {
            "description": "Request validation failed.",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDocument"},
                }
            },
        }
        for path in schema["paths"].values():
            for operation in path.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                responses = operation["responses"]
                automatic = responses.get("422", {})
                validation = automatic.get("content", {}).get("application/json", {})
                reference = validation.get("schema", {}).get("$ref")
                if reference == "#/components/schemas/HTTPValidationError":
                    responses.pop("422")
                    responses.setdefault("400", response)
                if any(value.get("in") == "path" for value in operation.get("parameters", [])):
                    responses.setdefault("404", {**response, "description": "Resource not found."})
        return schema
