from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from apps.audit.services import AuditAction, record

from . import features
from .access import AccessNote
from .models import PlatformPolicy
from .permissions import HasAdminPermission


class FeatureSerializer(serializers.Serializer):
    code = serializers.CharField()
    role = serializers.CharField()
    label = serializers.CharField()
    enabled = serializers.BooleanField()


class PolicyWriteSerializer(serializers.Serializer):
    disabled_features = serializers.ListField(child=serializers.ChoiceField(choices=sorted(features.FEATURE_CODES)))


class PlatformPolicyView(viewsets.GenericViewSet):
    permission_classes = [HasAdminPermission]
    queryset = PlatformPolicy.objects.none()
    serializer_class = FeatureSerializer
    action_permissions = {"retrieve": "platform.view", "partial_update": "platform.manage"}
    access_notes = {"*": AccessNote(conditions=("Admin faqat Super Admin bergan platform ruxsatlari bilan.",))}

    @extend_schema(summary="Rollar imkoniyatlarini ko'rish", tags=["platform"], responses=FeatureSerializer(many=True))
    def retrieve(self, request):
        return Response(features.catalog())

    @extend_schema(
        summary="Rollar imkoniyatlarini yoqish / o'chirish",
        tags=["platform"],
        request=PolicyWriteSerializer,
        responses=FeatureSerializer(many=True),
    )
    @transaction.atomic
    def partial_update(self, request):
        body = PolicyWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        PlatformPolicy.load()
        obj = PlatformPolicy.objects.select_for_update().get(pk=1)
        before = obj.disabled_features
        obj.disabled_features = sorted(set(body.validated_data["disabled_features"]))
        obj.save(update_fields=["disabled_features", "updated_at"])
        record(
            request,
            AuditAction.UPDATE,
            obj,
            changes={"disabled_features": {"from": before, "to": obj.disabled_features}},
        )
        return Response(features.catalog())
