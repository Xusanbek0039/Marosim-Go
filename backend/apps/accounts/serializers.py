from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.core.uploads import process_image
from apps.subscriptions.badges import PaidBadgeSerializer

from . import permissions_catalog as catalog
from . import phone as phone_utils
from . import pinfl as pinfl_utils
from .models import CLIENT_ROLES, Role, User, normalize_optional_email

DUPLICATE_PHONE = "Bu telefon raqam bilan hisob allaqachon mavjud."
EXAMPLE_PHONE = "+998901234567"
EXAMPLE_PASSWORD = "SecurePassword123!"


class PhoneNumberField(serializers.CharField):
    """Accepts local/international spellings, always yields E.164."""

    default_error_messages = {"invalid_phone": phone_utils.INVALID_MESSAGE}

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 32)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return phone_utils.normalize(value)
        except DjangoValidationError:
            self.fail("invalid_phone")


def ensure_phone_free(value: str, instance: User | None = None) -> str:
    qs = User.objects.filter(phone_number=value)  # soft-deleted rows still own their number
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError(DUPLICATE_PHONE, code="duplicate_phone")
    return value


def run_password_validators(password: str, candidate: User, field: str = "password") -> None:
    try:
        password_validation.validate_password(password, user=candidate)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({field: exc.messages}) from None


class UserSummarySerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """Compact, safe representation used inside other resources (studios, dashboard)."""

    full_name = serializers.CharField(read_only=True)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "is_verified",
            "id",
            "phone_number",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "profile_picture",
            "pinfl_masked",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class MeSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """The caller's own profile. PINFL is only ever exposed masked."""

    full_name = serializers.CharField(read_only=True)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "is_verified",
            "id",
            "phone_number",
            "is_phone_verified",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "profile_picture",
            "address",
            "pinfl_masked",
            "permissions",
            "last_login",
            "created_at",
        ]
        read_only_fields = fields

    def get_permissions(self, obj) -> list[str]:
        return obj.effective_permissions()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Profilni yangilash",
            value={"first_name": "Dilnoza", "last_name": "Karimova", "address": "Toshkent, Chilonzor"},
            request_only=True,
        )
    ]
)
class MeUpdateSerializer(serializers.ModelSerializer):
    """Self-service profile edit. Everything security-relevant (role, flags, phone, PINFL) is absent on purpose."""

    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "profile_picture", "address"]
        extra_kwargs = {
            "first_name": {"max_length": 100, "required": False},
            "last_name": {"max_length": 100, "required": False},
            "address": {"max_length": 255, "required": False, "allow_blank": True},
        }

    def validate_first_name(self, value: str) -> str:
        return value.strip()

    def validate_last_name(self, value: str) -> str:
        return value.strip()

    def validate_address(self, value: str) -> str:
        return value.strip()

    def validate_profile_picture(self, value):
        return process_image(value) if value else value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Ro'yxatdan o'tish",
            value={"phone_number": EXAMPLE_PHONE, "password": EXAMPLE_PASSWORD, "password_confirm": EXAMPLE_PASSWORD},
            request_only=True,
        )
    ]
)
class RegisterSerializer(serializers.Serializer):
    """Public sign-up. The role is always USER; any role/flag sent by the client is ignored."""

    phone_number = PhoneNumberField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128, style={"input_type": "password"}
    )

    def validate_phone_number(self, value: str) -> str:
        return ensure_phone_free(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": ["Parollar mos kelmadi."]})
        run_password_validators(attrs["password"], User(phone_number=attrs["phone_number"]))
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    phone_number=validated_data["phone_number"],
                    password=validated_data["password"],
                    role=Role.USER,
                )
        except IntegrityError:  # lost a race against a concurrent sign-up with the same number
            raise serializers.ValidationError({"phone_number": [DUPLICATE_PHONE]}) from None


class ManagedUserSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """Create/update/read accounts managed by the panel.

    ``pinfl`` and ``password`` are write-only; reads only ever expose ``pinfl_masked``.
    """

    allowed_roles: tuple[str, ...] = tuple(r.value for r in CLIENT_ROLES)

    phone_number = PhoneNumberField(required=False)
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        trim_whitespace=False,
        style={"input_type": "password"},
        min_length=10,
        max_length=128,
    )
    pinfl = serializers.CharField(write_only=True, required=False, max_length=32)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)
    full_name = serializers.CharField(read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    role = serializers.ChoiceField(choices=[], required=False)

    class Meta:
        model = User
        fields = [
            "is_verified",
            "id",
            "phone_number",
            "is_phone_verified",
            "email",
            "password",
            "first_name",
            "last_name",
            "full_name",
            "pinfl",
            "pinfl_masked",
            "profile_picture",
            "address",
            "role",
            "is_active",
            "last_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_phone_verified", "last_login", "created_at", "updated_at"]
        extra_kwargs = {
            "first_name": {"max_length": 100},
            "last_name": {"max_length": 100},
            "address": {"max_length": 255, "required": False, "allow_blank": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [(r, Role(r).label) for r in self.allowed_roles]

    # --------------------------------------------------------------- validation
    def validate_phone_number(self, value: str) -> str:
        return ensure_phone_free(value, self.instance)

    def validate_email(self, value: str | None) -> str | None:
        value = normalize_optional_email(value)
        if value is None:
            return None
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu email bilan hisob allaqachon mavjud.")
        return value

    def validate_pinfl(self, value: str) -> str:
        try:
            value = pinfl_utils.validate(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from None
        qs = User.objects.filter(pinfl_hash=pinfl_utils.hash_of(value))
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu JSHSHIR boshqa hisobga biriktirilgan.")
        return value

    def validate_profile_picture(self, value):
        return process_image(value) if value else value

    def validate_first_name(self, value: str) -> str:
        return value.strip()

    def validate_last_name(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs):
        creating = self.instance is None
        if self.instance and attrs.get("role", self.instance.role) != self.instance.role:
            if self.instance.responsible_studios.filter(is_active=True, deleted_at__isnull=True).exists():
                raise serializers.ValidationError({"role": ["Avval studiya egaligini boshqa shaxsga o'tkazing."]})
            if self.instance.venue_memberships.filter(
                is_active=True, role="OWNER", venue__is_active=True, venue__deleted_at__isnull=True
            ).exists():
                raise serializers.ValidationError({"role": ["Avval to'yxona egaligini boshqa shaxsga o'tkazing."]})
        if creating:
            missing = {
                name: "Bu maydon to'ldirilishi shart."
                for name in ("phone_number", "password", "pinfl", "first_name", "last_name")
                if not attrs.get(name)
            }
            if missing:
                raise serializers.ValidationError(missing)

        password = attrs.get("password")
        if password:
            candidate = self.instance or User(
                phone_number=attrs.get("phone_number"),
                email=attrs.get("email"),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            run_password_validators(password, candidate)
        return attrs

    # ------------------------------------------------------------------- writes
    def default_role(self) -> str:
        return Role.USER

    def create(self, validated_data):
        password = validated_data.pop("password")
        pinfl = validated_data.pop("pinfl")
        validated_data.setdefault("role", self.default_role())
        user = User(**validated_data)
        user.set_password(password)
        user.set_pinfl(pinfl)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        pinfl = validated_data.pop("pinfl", None)
        if "phone_number" in validated_data and validated_data["phone_number"] != instance.phone_number:
            # A new number has not been proven to belong to the person.
            instance.is_phone_verified = False
            instance.phone_verified_at = None
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        if pinfl:
            instance.set_pinfl(pinfl)
        instance.save()
        return instance


class AdminSerializer(ManagedUserSerializer):
    allowed_roles = (Role.ADMIN.value,)

    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=list(catalog.ALL_CODES)),
        source="admin_permissions",
        required=False,
        allow_empty=True,
        max_length=len(catalog.ALL_CODES),
    )

    class Meta(ManagedUserSerializer.Meta):
        fields = [*ManagedUserSerializer.Meta.fields, "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].read_only = True

    def default_role(self) -> str:
        return Role.ADMIN

    def validate_permissions(self, value):
        return catalog.normalize(value)

    def create(self, validated_data):
        validated_data["role"] = Role.ADMIN
        validated_data.setdefault("admin_permissions", list(catalog.DEFAULT_ADMIN_PERMISSIONS))
        return super().create(validated_data)


class PermissionDefSerializer(serializers.Serializer):
    code = serializers.CharField()
    module = serializers.CharField()
    module_label = serializers.CharField()
    label = serializers.CharField()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Telefon va parol", value={"phone_number": EXAMPLE_PHONE, "password": EXAMPLE_PASSWORD}, request_only=True
        )
    ]
)
class LoginSerializer(serializers.Serializer):
    # Deliberately a plain CharField: a malformed number gets the same generic 401 as a wrong one.
    phone_number = serializers.CharField(max_length=32)
    password = serializers.CharField(trim_whitespace=False, max_length=128, style={"input_type": "password"})


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class TokenPairSerializer(serializers.Serializer):
    """Body of login/register/refresh. Tokens are only in the body for ``X-Client: mobile``;
    the web panel receives them as httpOnly cookies instead."""

    user = MeSerializer()
    access = serializers.CharField(required=False, help_text="Faqat X-Client: mobile")
    refresh = serializers.CharField(required=False, help_text="Faqat X-Client: mobile")


class PinflRevealSerializer(serializers.Serializer):
    pinfl = serializers.CharField()


class AccountFeatureSerializer(serializers.Serializer):
    code = serializers.CharField()
    role = serializers.CharField()
    label = serializers.CharField()
    enabled = serializers.BooleanField(help_text="Shu hisob uchun yoqilganmi")
    platform_enabled = serializers.BooleanField(help_text="Platforma boshqaruvida (butun rol uchun) yoqilganmi")


class AccountFeaturesWriteSerializer(serializers.Serializer):
    disabled_features = serializers.ListField(child=serializers.CharField(max_length=64), max_length=50)
