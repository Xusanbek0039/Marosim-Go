from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q

from apps.core import crypto
from apps.core.models import BaseModel, SoftDeleteModel

from . import pinfl as pinfl_utils
from .permissions_catalog import ALL_CODES


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    STUDIO = "STUDIO", "Studiya"
    USER = "USER", "Foydalanuvchi"


#: Roles managed through /api/v1/users/ (admins have their own endpoint; super admins none).
CLIENT_ROLES = (Role.USER, Role.STUDIO)


def avatar_upload_to(instance, filename):
    return f"avatars/{filename}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required.")
        raw_pinfl = extra.pop("pinfl", None)
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        if raw_pinfl:
            user.set_pinfl(raw_pinfl)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("role", Role.USER)
        if extra["role"] == Role.SUPER_ADMIN:
            raise ValueError("Use create_superuser for SUPER_ADMIN accounts.")
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        """Only reachable from the CLI (``manage.py createsuperuser``) — never from the API."""
        extra["role"] = Role.SUPER_ADMIN
        extra["is_staff"] = True
        return self._create(email, password, **extra)

    def alive(self):
        return self.filter(deleted_at__isnull=True)


class User(BaseModel, SoftDeleteModel, AbstractBaseUser):
    email = models.EmailField("email", unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # PINFL / JSHSHIR — never stored in plaintext.
    pinfl_encrypted = models.TextField(blank=True, editable=False)
    pinfl_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    pinfl_last4 = models.CharField(max_length=4, blank=True, editable=False)

    profile_picture = models.ImageField(upload_to=avatar_upload_to, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, db_index=True)
    admin_permissions = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # Bumped to invalidate every issued token at once (deactivate, password change, token reuse).
    auth_version = models.PositiveIntegerField(default=1, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["role", "is_active"])]
        constraints = [
            models.CheckConstraint(condition=Q(role__in=[r.value for r in Role]), name="accounts_user_role_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    # ---------------------------------------------------------------- identity
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    # ------------------------------------------------------------------- PINFL
    def set_pinfl(self, raw: str | None) -> None:
        if not raw:
            self.pinfl_encrypted, self.pinfl_hash, self.pinfl_last4 = "", None, ""
            return
        value = pinfl_utils.validate(raw)
        self.pinfl_encrypted = crypto.encrypt(value)
        self.pinfl_hash = pinfl_utils.hash_of(value)
        self.pinfl_last4 = value[-4:]

    def get_pinfl(self) -> str | None:
        return crypto.decrypt(self.pinfl_encrypted) if self.pinfl_encrypted else None

    @property
    def pinfl_masked(self) -> str | None:
        return pinfl_utils.mask(self.pinfl_last4)

    # ------------------------------------------------------------- permissions
    def effective_permissions(self) -> list[str]:
        if not self.is_active or self.is_deleted:
            return []
        if self.role == Role.SUPER_ADMIN:
            return list(ALL_CODES)
        if self.role == Role.ADMIN:
            return [c for c in self.admin_permissions if c in ALL_CODES]
        return []

    def has_admin_permission(self, code: str) -> bool:
        return code in self.effective_permissions()
