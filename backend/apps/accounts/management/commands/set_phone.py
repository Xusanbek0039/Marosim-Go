"""Assign (or change) the login phone of an existing account.

Accounts created before v2 signed in with email and have no phone yet; they cannot log in
until one is assigned:

    python manage.py set_phone admin@marosimgo.uz +998901234567
    python manage.py set_phone --list-missing
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts import phone as phone_utils
from apps.accounts.models import User
from apps.accounts.tokens import revoke_all_sessions


class Command(BaseCommand):
    help = "Set the login phone number of an account identified by email or id."

    def add_arguments(self, parser):
        parser.add_argument("account", nargs="?", help="Email or user id (UUID)")
        parser.add_argument("phone", nargs="?", help="Phone number, e.g. +998901234567")
        parser.add_argument("--list-missing", action="store_true", help="List accounts that have no phone yet")

    def handle(self, *args, account=None, phone=None, list_missing=False, **options):
        if list_missing:
            rows = User.objects.alive().filter(phone_number__isnull=True).order_by("role", "email")
            for user in rows:
                self.stdout.write(f"{user.pk}  {user.role:<12} {user.email or '-'}")
            self.stdout.write(self.style.SUCCESS(f"{rows.count()} account(s) without a phone number."))
            return
        if not account or not phone:
            raise CommandError("Usage: set_phone <email|id> <phone>  (or --list-missing)")

        try:
            normalized = phone_utils.normalize(phone)
        except ValidationError as exc:
            raise CommandError(exc.messages[0]) from None

        user = self._find(account)
        clash = User.objects.filter(phone_number=normalized).exclude(pk=user.pk).first()
        if clash is not None:
            raise CommandError(f"{normalized} is already used by account {clash.pk}.")

        with transaction.atomic():
            user.phone_number = normalized
            user.is_phone_verified = False
            user.phone_verified_at = None
            user.save(update_fields=["phone_number", "is_phone_verified", "phone_verified_at", "updated_at"])
            revoke_all_sessions(user)
        self.stdout.write(self.style.SUCCESS(f"{user.email or user.pk}: login phone set to {normalized}."))

    @staticmethod
    def _find(account: str) -> User:
        qs = User.objects.alive()
        user = qs.filter(email__iexact=account.strip()).first()
        if user is None:
            try:
                user = qs.filter(pk=account).first()
            except ValidationError:
                user = None
        if user is None:
            raise CommandError(f"Account not found: {account}")
        return user
