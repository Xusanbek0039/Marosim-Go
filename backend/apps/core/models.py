import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """UUID primary key + timestamps for every domain model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Rows are never hard-deleted through the API: ``deleted_at`` hides them instead."""

    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])
