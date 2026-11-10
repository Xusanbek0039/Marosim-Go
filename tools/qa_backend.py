"""Disposable local UI audit server. Never touches backend/db.sqlite3 or external storage."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
(ROOT / ".qa").mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/.venv/Lib/site-packages"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"
os.environ["DATABASE_URL"] = "sqlite:///" + (ROOT / ".qa/ui.sqlite3").as_posix()
os.environ["DJANGO_DEBUG"] = "true"
os.environ["AUTH_COOKIE_SECURE"] = "false"

import django
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", ".localhost"]
settings.AUTH_COOKIE_SECURE = False
settings.CSRF_TRUSTED_ORIGINS = ["http://*.localhost:8100", *[f"http://127.0.0.1:{port}" for port in range(3100, 3104)]]
settings.PANEL_HOST_SITES = {"sa.localhost": "superadmin", "ad.localhost": "admin", "st.localhost": "studio", "us.localhost": "userlogin", "ve.localhost": "toyxona"}
settings.DEBUG = True
from django.core.management import call_command
from django.utils import timezone
from apps.accounts.models import Role, User
from apps.accounts.permissions_catalog import ALL_CODES
from apps.studios.models import Studio, StudioMembership
from apps.venues.models import Venue, VenueMembership, VenueHall, HallSession
from apps.ceremonies.models import Ceremony, CeremonyOwnership
from apps.subscriptions.models import SubscriptionPlan
from apps.subscriptions.services import grant
from types import SimpleNamespace
from datetime import date, time, timedelta

if sys.argv[1:] == ["setup"]:
    call_command("migrate", verbosity=0)
    people = {}
    for n, role in enumerate([Role.SUPER_ADMIN, Role.ADMIN, Role.STUDIO, Role.VENUE_OWNER, Role.USER], 1):
        user, _ = User.objects.get_or_create(phone_number=f"+99890111000{n}", defaults={"role": role, "first_name": "QA", "last_name": role, "admin_permissions": list(ALL_CODES) if role == Role.ADMIN else [], "is_phone_verified": True})
        user.set_password("Local-Audit-2026!")
        user.save()
        people[role] = user
    studio, _ = Studio.objects.get_or_create(name="QA Studio", defaults={"address": "Toshkent", "description": "Sinov studiyasi", "responsible_user": people[Role.STUDIO]})
    StudioMembership.objects.get_or_create(studio=studio, user=people[Role.STUDIO], defaults={"role": "OWNER"})
    venue, _ = Venue.objects.get_or_create(name="QA To'yxona", defaults={"address": "Toshkent", "capacity_max": 250, "base_price": "15000000", "publication_status": "APPROVED", "region": "TASHKENT_CITY"})
    VenueMembership.objects.get_or_create(venue=venue, user=people[Role.VENUE_OWNER], defaults={"role": "OWNER"})
    hall, _ = VenueHall.objects.get_or_create(venue=venue, name="Asosiy zal", defaults={"capacity": 250})
    HallSession.objects.get_or_create(hall=hall, name="Kechki", defaults={"starts_at": time(18), "ends_at": time(23)})
    ceremony, _ = Ceremony.objects.get_or_create(studio=studio, title="QA To'y", defaults={"event_date": date.today() + timedelta(days=10), "created_by": people[Role.STUDIO], "status": "READY"})
    CeremonyOwnership.objects.get_or_create(ceremony=ceremony, user=people[Role.USER], defaults={"status": "ACCEPTED", "owner_type": "BRIDE", "accepted_at": timezone.now()})
    for user, code, target in [(people[Role.USER], "M1", {}), (people[Role.STUDIO], "STUDIO_M1", {"studio": studio}), (people[Role.VENUE_OWNER], "VENUE_M1", {"venue": venue})]:
        if not user.subscriptions.exists():
            grant(SimpleNamespace(user=people[Role.SUPER_ADMIN], META={}), user, SubscriptionPlan.objects.get(code=code), **target)
    print("Disposable QA database ready")
else:
    call_command("runserver", "127.0.0.1:8100", use_reloader=False)
