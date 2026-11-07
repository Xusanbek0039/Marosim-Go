"""API endpoint catalog built from the live OpenAPI schema (drf-spectacular).

Nothing is hand-maintained: a new view shows up here as soon as it is routed. The schema is
generated once per process and cached for ``CATALOG_TTL_SECONDS`` (URLconf only changes on
deploy/reload anyway).

Examples are documentation only: placeholders for secrets (``<ACCESS_TOKEN>``) and obviously
fake values — never real credentials or data.
"""

import threading
import time
from copy import deepcopy

from drf_spectacular.generators import SchemaGenerator

from .writer import cfg

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

#: Field-name based placeholders win over type-based ones.
NAMED_EXAMPLES = {
    "phone_number": "+998901234567",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "access": "<ACCESS_TOKEN>",
    "refresh": "<REFRESH_TOKEN>",
    "pinfl": "<JSHSHIR_14_RAQAM>",
    "pinfl_masked": "**********1234",
    "email": "user@example.uz",
    "first_name": "Dilnoza",
    "last_name": "Karimova",
    "full_name": "Dilnoza Karimova",
    "address": "Toshkent, Chilonzor",
    "name": "Nur Studio",
}
FORMAT_EXAMPLES = {
    "uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "date-time": "2026-01-15T10:30:00+05:00",
    "date": "2026-01-15",
    "email": "user@example.uz",
    "uri": "https://example.uz/media/avatars/example.webp",
    "binary": "<FILE>",
}

_cache: dict = {"at": 0.0, "schema": None}
_lock = threading.Lock()


def get_schema() -> dict:
    ttl = cfg()["CATALOG_TTL_SECONDS"]
    with _lock:
        if _cache["schema"] is None or time.monotonic() - _cache["at"] > ttl:
            _cache["schema"] = SchemaGenerator().get_schema(request=None, public=True)
            _cache["at"] = time.monotonic()
        return _cache["schema"]


def reset_cache() -> None:
    with _lock:
        _cache["schema"] = None


# ----------------------------------------------------------------- examples
def _resolve(schema: dict, components: dict) -> dict:
    ref = schema.get("$ref")
    if ref:
        return components.get(ref.rsplit("/", 1)[-1], {})
    if "allOf" in schema and schema["allOf"]:
        merged: dict = {}
        for part in schema["allOf"]:
            part = _resolve(part, components)
            merged = {**merged, **part, "properties": {**merged.get("properties", {}), **part.get("properties", {})}}
        return merged
    for key in ("oneOf", "anyOf"):
        if schema.get(key):
            return _resolve(schema[key][0], components)
    return schema


def example_for(schema: dict | None, components: dict, name: str = "", depth: int = 0):
    if not schema or depth > 6:
        return None
    schema = _resolve(schema, components)
    if "example" in schema:
        return schema["example"]
    if name in NAMED_EXAMPLES and schema.get("type") in (None, "string"):
        return NAMED_EXAMPLES[name]
    if schema.get("enum"):
        return next((v for v in schema["enum"] if v not in (None, "")), schema["enum"][0])

    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        return {key: example_for(sub, components, key, depth + 1) for key, sub in props.items()}
    if kind == "array":
        item = example_for(schema.get("items"), components, name, depth + 1)
        return [] if item is None else [item]
    if kind == "string":
        return FORMAT_EXAMPLES.get(schema.get("format"), "string")
    if kind == "integer":
        return 1
    if kind == "number":
        return 12.5
    if kind == "boolean":
        return True
    return None


def _request_example(op: dict, components: dict):
    content = (op.get("requestBody") or {}).get("content") or {}
    media = content.get("application/json") or next(iter(content.values()), None)
    if not media:
        return None, None
    content_type = "application/json" if "application/json" in content else next(iter(content))
    examples = media.get("examples") or {}
    for example in examples.values():
        if "value" in example:
            return deepcopy(example["value"]), content_type
    return example_for(media.get("schema"), components), content_type


def _success_response(op: dict, components: dict):
    for code, response in sorted(op.get("responses", {}).items()):
        if not code.startswith("2"):
            continue
        media = (response.get("content") or {}).get("application/json")
        body = example_for(media.get("schema"), components) if media else None
        return int(code), body
    return None, None


# ------------------------------------------------------------------- catalog
def build(schema: dict | None = None) -> list[dict]:
    schema = schema or get_schema()
    components = schema.get("components", {}).get("schemas", {})
    endpoints = []
    for path, item in schema.get("paths", {}).items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if not op:
                continue
            access = op.get("x-access") or {"auth_required": True, "roles": [], "permission": None, "label": ""}
            policy = op.get("x-access-policy") or {}
            docs = op.get("x-documentation") or {"status": "MISSING", "missing": ["x-documentation"]}
            request_example, content_type = _request_example(op, components)
            success_status, response_example = _success_response(op, components)
            endpoints.append(
                {
                    "id": op.get("operationId") or f"{method}:{path}",
                    "method": method.upper(),
                    "path": path,
                    "summary": op.get("summary", ""),
                    "description": op.get("description", ""),
                    "tags": op.get("tags", []),
                    "deprecated": bool(op.get("deprecated")),
                    "auth_required": access["auth_required"],
                    "roles": access["roles"],
                    "permission": access["permission"],
                    "access_label": access["label"],
                    # Role metadata (apps.accounts.access) — derived from the real permission classes.
                    "allowed_roles": op.get("x-allowed-roles", []),
                    "auth_type": op.get("x-auth-type", "UNKNOWN"),
                    "required_permissions": op.get("x-required-permissions", []),
                    "role_requirements": policy.get("role_requirements", {}),
                    "ownership_scope": op.get("x-ownership-scope"),
                    "conditions": op.get("x-access-conditions", []),
                    "permission_classes": policy.get("permission_classes", []),
                    "access_status": op.get("x-access-status", "REVIEW_REQUIRED"),
                    "review_reasons": policy.get("review_reasons", []),
                    "documentation_status": docs["status"],
                    "documentation_missing": docs["missing"],
                    "api_version": op.get("x-api-version", ""),
                    "parameters": [
                        {
                            "name": p.get("name"),
                            "in": p.get("in"),
                            "required": bool(p.get("required")),
                            "type": (p.get("schema") or {}).get("type", "string"),
                            "description": p.get("description", ""),
                        }
                        for p in op.get("parameters", [])
                    ],
                    "request_content_type": content_type,
                    "request_example": request_example,
                    "success_status": success_status,
                    "response_example": response_example,
                    "responses": [
                        {"status": int(code), "description": r.get("description", "")}
                        for code, r in sorted(op.get("responses", {}).items())
                        if code.isdigit()
                    ],
                }
            )
    endpoints.sort(key=lambda e: (e["path"], HTTP_METHODS.index(e["method"].lower())))
    return endpoints
