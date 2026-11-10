from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import PlatformPolicy, Role
from apps.studios.serializers import PublicStudioSerializer
from apps.subscriptions import services
from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.venues.models import Venue, VenueMembership
from apps.venues.serializers import PublicVenueSerializer

MINE = "/api/v1/me/subscriptions/"
ADMIN = "/api/v1/admin/subscriptions/"
POLICY = "/api/v1/admin/platform-policy/"


@pytest.fixture(params=["STUDIO", "VENUE"])
def business(request, make_user, make_studio):
    kind = request.param
    owner = make_user(Role.STUDIO if kind == "STUDIO" else Role.VENUE_OWNER)
    if kind == "STUDIO":
        target = make_studio(owner)
        serializer = PublicStudioSerializer
    else:
        target = Venue.objects.create(name="Test to'yxona", address="Toshkent", capacity_max=100, base_price=100)
        VenueMembership.objects.create(venue=target, user=owner, role="OWNER")
        serializer = PublicVenueSerializer
    return owner, target, serializer, SubscriptionPlan.objects.get(code=f"{kind}_M1")


def body_for(target, plan):
    return {target._meta.model_name: str(target.pk), "plan": str(plan.pk)}


@pytest.mark.django_db
def test_business_badge_requires_payment_and_expires(business, client_for, super_admin):
    owner, target, serializer, plan = business
    client = client_for(owner)
    assert serializer(target).data["is_verified"] is False
    pending = client.post(MINE, body_for(target, plan))
    assert pending.status_code == 201
    assert serializer(target).data["is_verified"] is False
    assert client.post(MINE, body_for(target, plan)).status_code == 400
    approved = client_for(super_admin).post(f"{ADMIN}{pending.data['id']}/approve/", {})
    assert approved.status_code == 200
    assert serializer(target).data["is_verified"] is True
    assert not services.has_clean_access(owner)  # a business badge grants no personal-media access
    assert client.get("/api/v1/auth/me/").data["is_verified"] is False
    status = client.get(f"{MINE}status/", {target._meta.model_name: str(target.pk)})
    assert status.data["is_verified"] is True
    assert all(p["audience"] == plan.audience for p in status.data["plans"])
    Subscription.objects.filter(pk=pending.data["id"]).update(ends_at=timezone.now() - timedelta(seconds=1))
    assert serializer(target).data["is_verified"] is False


@pytest.mark.django_db
def test_business_purchase_ownership_and_plan_scope(business, make_user, client_for):
    owner, target, serializer, plan = business
    stranger = client_for(make_user(owner.role))
    assert stranger.post(MINE, body_for(target, plan)).status_code == 400
    assert stranger.get(f"{MINE}status/", {target._meta.model_name: str(target.pk)}).status_code == 400
    client = client_for(owner)
    assert client.get(f"{MINE}status/", {target._meta.model_name: "bad-uuid"}).status_code == 400
    assert client.get(f"{MINE}status/").status_code == 400
    assert client.post(MINE, {"plan": str(plan.pk)}).status_code == 400
    assert client.post(MINE, body_for(target, SubscriptionPlan.objects.get(code="M1"))).status_code == 400
    pending = client.post(MINE, body_for(target, plan)).data
    assert stranger.post(f"{MINE}{pending['id']}/cancel/").status_code == 404
    assert client.get(f"{MINE}targets/").data[0]["id"] == str(target.pk)


@pytest.mark.django_db
def test_business_badge_cancellation_and_staff_permissions(business, make_user, client_for, super_admin):
    owner, target, serializer, plan = business
    viewer = client_for(make_user(Role.ADMIN, admin_permissions=["subscriptions.view"]))
    seller_user = make_user(Role.ADMIN, admin_permissions=["subscriptions.create", "subscriptions.update"])
    seller = client_for(seller_user)
    body = {"user_id": str(owner.pk), **body_for(target, plan)}
    assert viewer.post(ADMIN, body).status_code == 403
    created = seller.post(ADMIN, body)
    assert created.status_code == 201
    assert serializer(target).data["is_verified"] is True
    assert viewer.post(f"{ADMIN}{created.data['id']}/cancel/").status_code == 403
    # Permission removal is effective even for an already-issued JWT.
    client_for(super_admin).patch(f"/api/v1/admins/{seller_user.pk}/", {"permissions": []}, format="json")
    assert seller.post(f"{ADMIN}{created.data['id']}/cancel/").status_code == 403
    assert client_for(super_admin).post(f"{ADMIN}{created.data['id']}/cancel/").status_code == 200
    assert serializer(target).data["is_verified"] is False


@pytest.mark.django_db
def test_badge_does_not_spread_to_other_studios(make_user, make_studio, client_for, super_admin):
    owner = make_user(Role.STUDIO)
    first, second = make_studio(owner, name="One"), make_studio(owner, name="Two")
    plan = SubscriptionPlan.objects.get(code="STUDIO_M1")
    admin = client_for(super_admin)
    for target in (first, second):
        assert client_for(owner).post(MINE, body_for(target, plan)).status_code == 201
    sub = Subscription.objects.get(studio=first)
    admin.post(f"{ADMIN}{sub.pk}/approve/", {})
    rows = PublicStudioSerializer([first, second], many=True).data
    assert [r["is_verified"] for r in rows] == [True, False]
    renewal = admin.post(ADMIN, {"user_id": str(owner.pk), **body_for(first, plan)})
    sub.refresh_from_db()
    assert parse_datetime(renewal.data["starts_at"]) == sub.ends_at
    assert renewal.data["state"] == "SCHEDULED"


@pytest.mark.django_db
def test_user_badge_is_read_only_and_follows_subscription(plain_user, client_for, super_admin):
    user = client_for(plain_user)
    assert user.patch("/api/v1/auth/me/", {"is_verified": True}, format="json").data["is_verified"] is False
    sub = client_for(super_admin).post(
        ADMIN, {"user_id": str(plain_user.pk), "plan": str(SubscriptionPlan.objects.get(code="M1").pk)}
    )
    assert sub.status_code == 201
    assert user.get("/api/v1/auth/me/").data["is_verified"] is True
    assert not user.get("/api/v1/auth/me/").data["is_phone_verified"]


@pytest.mark.django_db
def test_policy_is_delegated_only_by_super_admin(make_user, client_for, super_admin, plain_user):
    admin = make_user(Role.ADMIN, admin_permissions=[])
    client = client_for(admin)
    assert client.get(POLICY).status_code == 403
    root = client_for(super_admin)
    assert (
        root.patch(f"/api/v1/admins/{admin.pk}/", {"permissions": ["platform.view"]}, format="json").status_code == 200
    )
    assert client.get(POLICY).status_code == 200
    assert client.patch(POLICY, {"disabled_features": []}, format="json").status_code == 403
    root.patch(f"/api/v1/admins/{admin.pk}/", {"permissions": ["platform.view", "platform.manage"]}, format="json")
    assert client.patch(POLICY, {"disabled_features": ["USER.reviews"]}, format="json").status_code == 200
    # Neither direct API calls nor a user's existing session bypass the switch.
    response = client_for(plain_user).post("/api/v1/venues/00000000-0000-0000-0000-000000000001/like/")
    assert response.status_code == 403
    assert (
        client.patch(f"/api/v1/admins/{admin.pk}/", {"permissions": ["users.delete"]}, format="json").status_code == 403
    )
    assert client.patch(POLICY, {"disabled_features": ["SUPER_ADMIN.anything"]}, format="json").status_code == 400
    root.patch(POLICY, {"disabled_features": []}, format="json")
    assert client_for(plain_user).post("/api/v1/venues/00000000-0000-0000-0000-000000000001/like/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "feature", "url"),
    [
        (Role.USER, "sharing", "/api/v1/me/ceremonies/00000000-0000-0000-0000-000000000001/invitations/"),
        (Role.USER, "ceremonies", "/api/v1/me/ceremonies/"),
        (Role.USER, "bookings", "/api/v1/me/venue-bookings/"),
        (Role.STUDIO, "ceremonies", "/api/v1/studios/me/"),
        (Role.STUDIO, "portfolio", "/api/v1/studios/me/00000000-0000-0000-0000-000000000001/images/"),
        (Role.VENUE_OWNER, "venues", "/api/v1/venue-owner/venues/"),
    ],
)
def test_disabled_role_features_are_enforced(role, feature, url, make_user, client_for):
    PlatformPolicy.objects.create(pk=1, disabled_features=[f"{role}.{feature}"])
    assert client_for(make_user(role)).get(url).status_code == 403


@pytest.mark.django_db
def test_disabled_purchase_preserves_existing_purchase_history(plain_user, client_for):
    PlatformPolicy.objects.create(pk=1, disabled_features=["USER.subscriptions"])
    user = client_for(plain_user)
    assert user.post(MINE, {"plan": str(SubscriptionPlan.objects.get(code="M1").pk)}).status_code == 403
    assert user.get(MINE).status_code == 200
    assert user.get(f"{MINE}status/").data["purchase_enabled"] is False


@pytest.mark.django_db
def test_registration_can_be_disabled(anon):
    PlatformPolicy.objects.create(pk=1, disabled_features=["PUBLIC.registration"])
    assert anon.post("/api/v1/auth/register/", {}).status_code == 403


@pytest.mark.django_db
def test_business_owner_account_cannot_be_stranded(business, client_for, super_admin):
    owner, target, serializer, plan = business
    root = client_for(super_admin)
    url = f"/api/v1/users/{owner.pk}/"
    assert root.patch(url, {"role": "USER"}, format="json").status_code == 400
    assert root.patch(url, {"is_active": False}, format="json").status_code == 409
    assert root.delete(url).status_code == 409
    owner.refresh_from_db()
    assert owner.is_active and not owner.is_deleted


@pytest.mark.django_db
def test_normalized_plan_code_duplicate_is_validation_error(client_for, super_admin):
    response = client_for(super_admin).post(
        "/api/v1/admin/subscription-plans/",
        {
            "code": "m1",
            "name": "Duplicate",
            "duration_months": 1,
            "price": "100",
            "max_viewers": 10,
        },
        format="json",
    )
    assert response.status_code == 400
    assert SubscriptionPlan.objects.filter(code="M1").count() == 1
