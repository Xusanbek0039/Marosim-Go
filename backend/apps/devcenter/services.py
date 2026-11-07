"""Developer Center data: everything is derived from the live OpenAPI schema, the reviewed
contract/changelog and real request logs — nothing about endpoints is maintained here.

"Documented", "matches contract", "healthy" and "deprecated" are separate facts and are
reported separately: a documented endpoint is not necessarily working.
"""

from collections import Counter

from apps.accounts.access import ROLE_ORDER
from apps.monitoring import catalog, contract, services

from .mobile import MOBILE_APPS

EMPTY_TRAFFIC = {"count": 0, "client_errors": 0, "server_errors": 0, "avg_ms": None, "last_seen": None}


def endpoints() -> list[dict]:
    """Catalog entries with contract status and the last 24h of real traffic."""
    items = contract.annotate(catalog.build())
    stats = services.endpoint_stats()
    for item in items:
        live = stats.get((item["method"], item["path"]))
        item["traffic_24h"] = {k: live[k] for k in EMPTY_TRAFFIC} if live else dict(EMPTY_TRAFFIC)
        item["status"] = live["status"] if live else "idle"
    return items


def filter_endpoints(items: list[dict], *, role: str = "", version: str = "", method: str = "") -> list[dict]:
    return [
        e
        for e in items
        if (not role or role in e["allowed_roles"])
        and (not version or e["api_version"] == version)
        and (not method or e["method"] == method.upper())
    ]


def overview(items: list[dict]) -> dict:
    schema = catalog.get_schema()
    history = contract.load_changelog()
    return {
        "api_version": schema.get("info", {}).get("version", ""),
        "openapi_version": schema.get("openapi", ""),
        "schema_url": "/api/v1/schema/",
        "docs_url": "/api/v1/docs/",
        "versions": sorted({e["api_version"] for e in items}),
        "totals": {
            "operations": len(items),
            "documented": sum(e["documentation_status"] == "DOCUMENTED" for e in items),
            "documentation_missing": sum(e["documentation_status"] != "DOCUMENTED" for e in items),
            "review_required": sum(e["access_status"] == "REVIEW_REQUIRED" for e in items),
            "deprecated": sum(bool(e["deprecated"]) for e in items),
            "called_24h": sum(e["traffic_24h"]["count"] > 0 for e in items),
        },
        "roles": [{"role": role, "count": sum(role in e["allowed_roles"] for e in items)} for role in ROLE_ORDER],
        "methods": dict(Counter(e["method"] for e in items)),
        "contract": dict(Counter(e["contract_status"] for e in items)),
        "health": dict(Counter(e["status"] for e in items)),
        "tags": sorted({t for e in items for t in e["tags"]}),
        "last_change": history[-1] if history else None,
    }


def mobile_guide(items: list[dict]) -> list[dict]:
    by_id = {e["id"]: e for e in items}
    apps = []
    for app in MOBILE_APPS:
        features = []
        for feature in app.features:
            ops = [by_id[op] for op in feature.operations if op in by_id]
            missing = [op for op in feature.operations if op not in by_id]
            if not feature.operations:
                status = "PLANNED"
            elif missing:
                status = "INCOMPLETE"  # an operation it relies on disappeared — tests fail on this
            else:
                status = "AVAILABLE"
            features.append(
                {
                    "key": feature.key,
                    "label": feature.label,
                    "status": status,
                    "planned": feature.planned,
                    "missing_operations": missing,
                    "operations": [
                        {
                            "id": e["id"],
                            "method": e["method"],
                            "path": e["path"],
                            "summary": e["summary"],
                            "allowed_roles": e["allowed_roles"],
                            "status": e["status"],
                        }
                        for e in ops
                    ],
                }
            )
        apps.append({"key": app.key, "label": app.label, "role": app.role, "features": features})
    return apps
