import logging
from datetime import date, datetime
from uuid import UUID

from django.db.models import Model
from django.db.models.fields.files import FieldFile

from apps.core.net import client_ip, user_agent

from .models import AuditAction, AuditLog

logger = logging.getLogger("apps.audit")

#: Field names whose values must never reach the audit log.
SENSITIVE_FIELDS = frozenset(
    {"password", "pinfl", "pinfl_encrypted", "pinfl_hash", "pinfl_last4", "auth_version", "last_login"}
)


def _plain(value):
    if isinstance(value, (UUID, date, datetime)):
        return str(value)
    if isinstance(value, Model):
        return str(value.pk)
    if isinstance(value, FieldFile):
        return value.name or None
    return value


def snapshot(instance: Model, fields: list[str]) -> dict:
    data = {}
    for name in fields:
        if name in SENSITIVE_FIELDS:
            continue
        field = instance._meta.get_field(name)
        value = getattr(instance, field.attname)
        data[name] = _plain(value)
    return data


def diff(before: dict, after: dict, touched_sensitive: set[str] | None = None) -> dict:
    changes = {
        key: {"from": before.get(key), "to": after.get(key)} for key in after if before.get(key) != after.get(key)
    }
    for name in touched_sensitive or ():
        changes[name] = "[REDACTED]"
    return changes


def record(
    request,
    action: str,
    target: Model | None = None,
    *,
    changes: dict | None = None,
    actor=None,
    target_label: str = "",
) -> AuditLog:
    if actor is None and request is not None:
        user = getattr(request, "user", None)
        actor = user if getattr(user, "is_authenticated", False) else None

    entry = AuditLog.objects.create(
        actor=actor,
        actor_label=getattr(actor, "identifier", "") or "",
        action=action,
        target_type=target._meta.label if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        target_label=target_label or (str(target) if target is not None else ""),
        changes=changes or {},
        ip_address=client_ip(request) if request is not None else None,
        user_agent=user_agent(request) if request is not None else "",
    )
    logger.info("audit %s by=%s target=%s:%s", action, entry.actor_label or "-", entry.target_type, entry.target_id)
    return entry


__all__ = ["AuditAction", "record", "snapshot", "diff", "SENSITIVE_FIELDS"]
