"""Project AutoSchema: every operation documents who may call it and how it can fail.

* Role metadata derived from the view's real permission classes (``apps.accounts.access``):
  ``x-allowed-roles``, ``x-auth-type``, ``x-required-permissions``, ``x-ownership-scope``,
  ``x-access-conditions``, ``x-access-status`` (``DERIVED`` / ``REVIEW_REQUIRED``), the full
  policy in ``x-access-policy`` and the legacy ``x-access`` summary.
  These describe the enforcement — they never replace it.
* ``x-api-version`` and ``x-documentation`` (``DOCUMENTED`` / ``MISSING`` + what is missing).
* The access rule is also appended to the human description shown in Swagger UI.
* Standard error responses (400/401/403/404/429) using the single ``ErrorEnvelope`` shape
  produced by ``apps.core.exceptions.api_exception_handler`` are added where they apply.

New endpoints get all of this automatically — nothing to maintain by hand.
"""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import ResolvedComponent

ERROR_ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["code", "message", "details"],
            "properties": {
                "code": {"type": "string", "example": "validation_error"},
                "message": {"type": "string", "example": "Yuborilgan ma'lumotlar noto'g'ri."},
                "details": {
                    "type": "object",
                    "nullable": True,
                    "additionalProperties": True,
                    "example": {"phone_number": ["Telefon raqam noto'g'ri. Masalan: +998901234567"]},
                },
            },
        }
    },
}

ERROR_DESCRIPTIONS = {
    "400": "validation_error — maydonlar bo'yicha xatolar `details` ichida",
    "401": "not_authenticated / invalid_credentials / session_invalid",
    "403": "permission_denied — rol yoki ruxsat yetarli emas (yoki CSRF)",
    "404": "not_found",
    "429": "throttled / account_locked — `details.retry_after` soniyalarda",
}


#: Default description drf-spectacular gives a response nobody described.
UNDESCRIBED = {"", "No response body"}
NO_BODY_STATUSES = {"204", "301", "302", "304"}


def documentation_issues(operation: dict) -> list[str]:
    """What a developer must still add for this operation to count as documented."""
    issues = []
    if not (operation.get("summary") or "").strip():
        issues.append("summary")
    responses = operation.get("responses", {})
    successes = {code: r for code, r in responses.items() if code.startswith("2") or code in NO_BODY_STATUSES}
    if not successes:
        issues.append("success_response")
    for code, response in successes.items():
        undescribed = not response.get("content") and response.get("description", "") in UNDESCRIBED
        if code not in NO_BODY_STATUSES and undescribed:
            issues.append(f"response_schema:{code}")
    return issues


def api_version(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    return parts[1] if len(parts) > 1 and parts[0] == "api" and parts[1].startswith("v") else "unversioned"


class MarosimAutoSchema(AutoSchema):
    def get_operation(self, path, path_regex, path_prefix, method, registry):
        operation = super().get_operation(path, path_regex, path_prefix, method, registry)
        if operation is None:
            return None

        from apps.accounts.access import AUTHENTICATED_ROLES, resolve
        from apps.accounts.permissions import legacy_access

        policy = resolve(self.view, self.method)
        access = legacy_access(policy)
        operation["x-access"] = access
        operation["x-allowed-roles"] = list(policy.allowed_roles)
        operation["x-auth-type"] = policy.auth_type
        operation["x-required-permissions"] = list(policy.required_permissions)
        operation["x-ownership-scope"] = policy.ownership_scope or None
        operation["x-access-conditions"] = list(policy.conditions)
        operation["x-access-status"] = policy.status
        operation["x-access-policy"] = policy.as_dict()
        operation["x-api-version"] = api_version(path)
        rule = f"**Ruxsat:** {access['label']}"
        if policy.ownership_scope:
            rule += f"\n\n**Ma'lumot doirasi:** {policy.ownership_scope}"
        if policy.conditions:
            rule += "\n\n**Shartlar:**\n" + "\n".join(f"* {c}" for c in policy.conditions)
        operation["description"] = f"{operation.get('description', '').rstrip()}\n\n{rule}".strip()

        envelope = ResolvedComponent(
            name="ErrorEnvelope", type=ResolvedComponent.SCHEMA, object="ErrorEnvelope", schema=ERROR_ENVELOPE_SCHEMA
        )
        registry.register_on_missing(envelope)

        codes = ["429"]
        if "requestBody" in operation or self.method in ("POST", "PUT", "PATCH"):
            codes.append("400")
        if access["auth_required"] or "login" in path:
            codes.append("401")
        restricted = not policy.is_public and set(policy.allowed_roles) != AUTHENTICATED_ROLES
        if restricted or (access["auth_required"] and self.method not in ("GET", "HEAD", "OPTIONS")):
            codes.append("403")
        if "{" in path:
            codes.append("404")

        responses = operation.setdefault("responses", {})
        for code in sorted(codes):
            responses.setdefault(
                code,
                {"description": ERROR_DESCRIPTIONS[code], "content": {"application/json": {"schema": envelope.ref}}},
            )

        issues = documentation_issues(operation)
        operation["x-documentation"] = {"status": "MISSING" if issues else "DOCUMENTED", "missing": issues}
        return operation
