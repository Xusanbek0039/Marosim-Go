import io
import itertools
import shutil

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.tokens import issue_tokens
from apps.studios.models import Studio

PASSWORD = "Xavfsiz-Parol-2026"
_pinfl_seq = itertools.count(30101990000001)
_phone_seq = itertools.count(1)


def next_pinfl() -> str:
    return str(next(_pinfl_seq))


def next_phone() -> str:
    """Unique, valid Uzbek mobile numbers in E.164 (+99891xxxxxxx)."""
    return f"+99891{next(_phone_seq):07d}"


@pytest.fixture(autouse=True)
def _no_background_watermarks(settings):
    settings.MEDIA_WATERMARK_INLINE = False  # tests run the watermark jobs explicitly


@pytest.fixture(autouse=True)
def _clean_state():
    cache.clear()
    yield
    cache.clear()
    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)


@pytest.fixture
def make_user(db):
    counter = itertools.count(1)

    def factory(role=Role.USER, **extra) -> User:
        n = next(counter)
        data = {
            "phone_number": extra.pop("phone_number", next_phone()),
            "email": extra.pop("email", f"{role.lower()}{n}-{next_pinfl()}@example.uz"),
            "first_name": extra.pop("first_name", f"Ism{n}"),
            "last_name": extra.pop("last_name", f"Familiya{n}"),
            "pinfl": extra.pop("pinfl", next_pinfl()),
            **extra,
        }
        if role == Role.SUPER_ADMIN:
            data.pop("pinfl")
            return User.objects.create_superuser(password=PASSWORD, **data)
        return User.objects.create_user(password=PASSWORD, role=role, **data)

    return factory


@pytest.fixture
def super_admin(make_user):
    return make_user(Role.SUPER_ADMIN)


@pytest.fixture
def admin_user(make_user):
    return make_user(Role.ADMIN, admin_permissions=[])


@pytest.fixture
def studio_user(make_user):
    return make_user(Role.STUDIO)


@pytest.fixture
def plain_user(make_user):
    return make_user(Role.USER)


@pytest.fixture
def make_studio(db):
    def factory(owner, **extra) -> Studio:
        return Studio.objects.create(
            name=extra.pop("name", f"Studio {owner.pk.hex[:6]}"),
            address=extra.pop("address", "Toshkent"),
            responsible_user=owner,
            **extra,
        )

    return factory


def bearer_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)['access']}", HTTP_X_CLIENT="mobile")
    return client


@pytest.fixture
def client_for():
    return bearer_client


@pytest.fixture
def anon():
    return APIClient()


def image_file(name="avatar.png", fmt="PNG", size=(64, 64)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", size, (37, 99, 235)).save(buf, format=fmt)
    content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(fmt, "image/gif")
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


def subscribe(user, code: str = "M1"):
    """Give ``user`` a running subscription (as if an admin approved the payment)."""
    from django.utils import timezone

    from apps.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
    from apps.subscriptions.services import add_months

    plan = SubscriptionPlan.objects.get(code=code)
    now = timezone.now()
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        price=plan.price,
        duration_months=plan.duration_months,
        max_viewers=plan.max_viewers,
        starts_at=now,
        ends_at=add_months(now, plan.duration_months),
        paid_amount=plan.price,
    )
