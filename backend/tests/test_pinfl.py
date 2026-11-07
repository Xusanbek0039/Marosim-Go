import logging

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.accounts import pinfl
from apps.accounts.models import Role, User
from apps.core.logging import SensitiveDataFilter, redact


@pytest.mark.parametrize("raw", ["123", "1234567890123a", "123456789012345", "", "11111111111111"])
def test_invalid_pinfl_rejected(raw):
    with pytest.raises(ValidationError):
        pinfl.validate(raw)


def test_valid_pinfl_normalized():
    assert pinfl.validate("3120 1990-123456") == "31201990123456"


def test_pinfl_is_never_stored_in_plaintext(make_user):
    user = make_user(Role.USER, pinfl="31201990123456")
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM accounts_user WHERE id = %s", [user.pk.hex])
        row = cursor.fetchone()
    assert row is not None
    assert not any("31201990123456" in str(col) for col in row)
    fresh = User.objects.get(pk=user.pk)
    assert fresh.get_pinfl() == "31201990123456"
    assert fresh.pinfl_masked == "**********3456"
    assert fresh.pinfl_hash == pinfl.hash_of("31201990123456")


def test_log_redaction_hides_pinfl_and_secrets():
    assert "31201990123456" not in redact("user pinfl 31201990123456 created")
    assert "hunter2" not in redact('{"password": "hunter2"}')
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "pinfl=%s", ("31201990123456",), None)
    SensitiveDataFilter().filter(record)
    assert "31201990123456" not in record.getMessage()
