from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.uploads import process_image

from . import permissions_catalog as catalog
from . import pinfl as pinfl_utils
from .models import CLIENT_ROLES, Role, User


class UserSummarySerializer(serializers.ModelSerializer):
    """Compact, safe representation used inside other resources (studios, dashboard)."""

    full_name = serializers.CharField(read_only=True)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "role",
            "profile_picture", "pinfl_masked", "is_active", "created_at",
        ]
        read_only_fields = fields


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "role", "profile_picture",
            "address", "pinfl_masked", "permissions", "last_login", "created_at",
        ]
        read_only_fields = fields

    def get_permissions(self, obj) -> list[str]:
        return obj.effective_permissions()


class ManagedUserSerializer(serializers.ModelSerializer):
    """Create/update/read accounts managed by the panel.

    ``pinfl`` and ``password`` are write-only; reads only ever expose ``pinfl_masked``.
    """

    allowed_roles: tuple[str, ...] = tuple(r.value for r in CLIENT_ROLES)

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False, style={"input_type": "password"},
        min_length=10, max_length=128,
    )
    pinfl = serializers.CharField(write_only=True, required=False, max_length=32)
    pinfl_masked = serializers.CharField(read_only=True, allow_null=True)
    full_name = serializers.CharField(read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    role = serializers.ChoiceField(choices=[], required=False)

    class Meta:
        model = User
        fields = [
            "id", "email", "password", "first_name", "last_name", "full_name", "pinfl", "pinfl_masked",
            "profile_picture", "address", "role", "is_active", "last_login", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_login", "created_at", "updated_at"]
        extra_kwargs = {
            "first_name": {"max_length": 100},
            "last_name": {"max_length": 100},
            "address": {"max_length": 255, "required": False, "allow_blank": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [(r, Role(r).label) for r in self.allowed_roles]

    # --------------------------------------------------------------- validation
    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
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
        if creating:
            missing = {
                name: "Bu maydon to'ldirilishi shart."
                for name in ("password", "pinfl", "first_name", "last_name")
                if not attrs.get(name)
            }
            if missing:
                raise serializers.ValidationError(missing)

        password = attrs.get("password")
        if password:
            candidate = self.instance or User(
                email=attrs.get("email", ""),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            try:
                password_validation.validate_password(password, user=candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages}) from None
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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=128, style={"input_type": "password"})


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class PinflRevealSerializer(serializers.Serializer):
    pinfl = serializers.CharField()
