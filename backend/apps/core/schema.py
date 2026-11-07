"""Project AutoSchema: every operation documents who may call it and how it can fail.

* ``x-access`` — auth requirement, roles and permission code, derived from the view's real
  permission classes (``apps.accounts.permissions.describe_access``).
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


class MarosimAutoSchema(AutoSchema):
    def get_operation(self, path, path_regex, path_prefix, method, registry):
        operation = super().get_operation(path, path_regex, path_prefix, method, registry)
        if operation is None:
            return None

        from apps.accounts.permissions import describe_access

        access = describe_access(self.view)
        operation["x-access"] = access
        rule = f"**Ruxsat:** {access['label']}"
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
        if access["roles"] or (access["auth_required"] and self.method not in ("GET", "HEAD", "OPTIONS")):
            codes.append("403")
        if "{" in path:
            codes.append("404")

        responses = operation.setdefault("responses", {})
        for code in sorted(codes):
            responses.setdefault(
                code,
                {"description": ERROR_DESCRIPTIONS[code], "content": {"application/json": {"schema": envelope.ref}}},
            )
        return operation
