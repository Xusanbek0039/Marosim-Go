"""Personal folder names in "Mening marosimlarim".

Every ceremony a USER may open (as an owner — "o'z to'yi" — or a viewer it was shared with) is shown
as a folder. The folder name is per account: renaming never touches ``Ceremony.title`` that the
studio and the other members see. A blank name resets the folder to the ceremony title.
"""

from django.db import transaction
from django.db.models import Prefetch

from apps.audit.services import AuditAction, record

from . import ownership
from .models import AccessRole, Ceremony, CeremonyFolder

MAX_NAME = 100


def with_folders(queryset, user):
    """Prefetch ``user``'s own folder row as ``ceremony.my_folders`` (0 or 1 item)."""
    return queryset.prefetch_related(
        Prefetch("folders", queryset=CeremonyFolder.objects.filter(user=user), to_attr="my_folders")
    )


def custom_name(ceremony) -> str | None:
    rows = getattr(ceremony, "my_folders", None)
    if rows is None:
        return None
    return rows[0].name if rows else None


def user_folders(user):
    """The ceremonies ``user`` may open, with role and folder name — the panel view of one account."""
    from .serializers import with_owners  # serializers import this module's helpers too

    qs = with_folders(with_owners(ownership.accessible_ceremonies(user)), user).select_related("studio")
    rows = []
    for ceremony in qs.order_by("-event_date"):
        is_owner = any(o.user_id == user.pk for o in ceremony.accepted_owners)
        rows.append(
            {
                "ceremony": ceremony,
                "access_role": AccessRole.OWNER if is_owner else AccessRole.VIEWER,
                "custom_name": custom_name(ceremony),
            }
        )
    return rows


@transaction.atomic
def rename(request, user, ceremony: Ceremony, name: str) -> str | None:
    """Set (or with a blank ``name`` reset) ``user``'s folder name for ``ceremony``."""
    name = " ".join((name or "").split())[:MAX_NAME]
    before = CeremonyFolder.objects.filter(user=user, ceremony=ceremony).values_list("name", flat=True).first()
    if name and name != ceremony.title:
        CeremonyFolder.objects.update_or_create(user=user, ceremony=ceremony, defaults={"name": name})
        after = name
    else:
        CeremonyFolder.objects.filter(user=user, ceremony=ceremony).delete()
        after = None
    if before != after:
        record(
            request,
            AuditAction.UPDATE,
            ceremony,
            changes={"folder_name": {"from": before, "to": after}, "account": str(user.pk)},
        )
    return after
