import uuid

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Yaratildi"
    UPDATE = "UPDATE", "Tahrirlandi"
    DEACTIVATE = "DEACTIVATE", "Nofaol qilindi"
    ACTIVATE = "ACTIVATE", "Faollashtirildi"
    DELETE = "DELETE", "O'chirildi (soft)"
    PERMISSIONS_CHANGE = "PERMISSIONS_CHANGE", "Ruxsatlar o'zgartirildi"
    REGISTER = "REGISTER", "Ro'yxatdan o'tdi"
    LOGIN = "LOGIN", "Tizimga kirdi"
    LOGIN_FAILED = "LOGIN_FAILED", "Kirish muvaffaqiyatsiz"
    LOGIN_LOCKED = "LOGIN_LOCKED", "Hisob vaqtincha bloklandi"
    LOGOUT = "LOGOUT", "Tizimdan chiqdi"
    TOKEN_REUSE = "TOKEN_REUSE", "Refresh token qayta ishlatildi"
    PINFL_REVEAL = "PINFL_REVEAL", "JSHSHIR ko'rildi"
    PARTICIPANT_INVITE = "PARTICIPANT_INVITE", "Marosimga taklif yuborildi"
    PARTICIPANT_ACCEPT = "PARTICIPANT_ACCEPT", "Taklif qabul qilindi"
    PARTICIPANT_DECLINE = "PARTICIPANT_DECLINE", "Taklif rad etildi"
    PARTICIPANT_REVOKE = "PARTICIPANT_REVOKE", "Ishtirokchi olib tashlandi"
    OWNER_INVITE = "OWNER_INVITE", "Marosim egasi taklif qilindi"
    OWNER_ACCEPT = "OWNER_ACCEPT", "Egalik taklifi qabul qilindi"
    OWNER_REQUEST_APPROVE = "OWNER_REQUEST_APPROVE", "Yangi egani ega tasdiqladi"
    OWNER_REJECT = "OWNER_REJECT", "Egalik rad etildi"
    VIEWER_INVITE = "VIEWER_INVITE", "Ko'ruvchi taklif qilindi"
    VIEWER_ACCEPT = "VIEWER_ACCEPT", "Ko'rish taklifi qabul qilindi"
    INVITATION_DECLINE = "INVITATION_DECLINE", "Taklif rad etildi (ega/ko'ruvchi)"
    INVITATION_REVOKE = "INVITATION_REVOKE", "Taklif bekor qilindi"
    INVITATION_RESEND = "INVITATION_RESEND", "Taklif qayta yuborildi"
    ACCESS_REVOKE = "ACCESS_REVOKE", "Marosimga kirish huquqi bekor qilindi"
    RECIPIENT_LOOKUP = "RECIPIENT_LOOKUP", "Taklif oluvchi qidirildi"
    MEDIA_UPLOAD = "MEDIA_UPLOAD", "Media yuklandi"
    STORAGE_CONNECT = "STORAGE_CONNECT", "Google Drive ulandi"
    STORAGE_CONNECT_FAILED = "STORAGE_CONNECT_FAILED", "Google Drive ulanmadi"
    STORAGE_DISCONNECT = "STORAGE_DISCONNECT", "Google Drive uzildi"


class AuditLog(models.Model):
    """Append-only record of security-relevant and management actions.

    ``changes`` never contains secrets: sensitive fields are written as ``[REDACTED]``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=32, choices=AuditAction.choices)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    target_label = models.CharField(max_length=254, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_label} {self.action} {self.target_type}"

    def save(self, *args, **kwargs):
        if self._state.adding is False:
            raise ValueError("Audit log entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")
