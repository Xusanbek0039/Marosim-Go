"""Development-only demo data so the panel can be explored against the real API."""

import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role, User
from apps.studios.models import Studio

FIRST = ["Dilnoza", "Jasur", "Malika", "Sardor", "Gulnora", "Bekzod", "Shahnoza", "Aziz", "Nodira", "Otabek"]
LAST = [
    "Karimova",
    "Aliyev",
    "Yusupova",
    "Tojiyev",
    "Ergasheva",
    "Nazarov",
    "Qodirova",
    "Rahimov",
    "Saidova",
    "Hamidov",
]
CITIES = ["Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan", "Navoiy", "Xiva"]
STUDIOS = ["Nur Studio", "Oq Saroy Media", "To'yona Video", "Lola Studio", "Visol Production"]


def fake_pinfl() -> str:
    return str(secrets.choice("3456")) + "".join(secrets.choice("0123456789") for _ in range(13))


class Command(BaseCommand):
    help = "Create demo users, admins and studios (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Demo-Parol-2026", help="Password for every demo account")

    def handle(self, *args, password, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DJANGO_DEBUG=true.")

        created = 0
        for i in range(24):
            role = Role.STUDIO if i < len(STUDIOS) else Role.USER
            email = f"demo{i + 1}@marosimgo.uz"
            if User.objects.filter(email=email).exists():
                continue
            User.objects.create_user(
                email=email,
                password=password,
                first_name=FIRST[i % len(FIRST)],
                last_name=LAST[(i * 3) % len(LAST)],
                pinfl=fake_pinfl(),
                address=CITIES[i % len(CITIES)],
                role=role,
                is_active=i % 7 != 3,
            )
            created += 1

        for i, perms in enumerate([["dashboard.view", "users.view", "studios.view"], ["dashboard.view"]]):
            email = f"admin{i + 1}@marosimgo.uz"
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=FIRST[-1 - i],
                    last_name=LAST[-1 - i],
                    pinfl=fake_pinfl(),
                    role=Role.ADMIN,
                    admin_permissions=perms,
                )
                created += 1

        owners = User.objects.filter(role=Role.STUDIO, is_active=True, deleted_at__isnull=True)
        for name, owner in zip(STUDIOS, owners, strict=False):
            Studio.objects.get_or_create(name=name, defaults={"address": owner.address, "responsible_user": owner})

        self.stdout.write(self.style.SUCCESS(f"Demo data ready ({created} new accounts). Password: {password}"))
