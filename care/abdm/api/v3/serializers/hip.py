from typing import Any

from rest_framework.exceptions import APIException
from rest_framework.serializers import CharField, ListField, Serializer, UUIDField

from care.utils.queryset.consultation import get_consultation_queryset


class LinkCarecontextSerializer(Serializer):
    consultations = ListField(child=UUIDField(), required=True)

    def validate(self, attrs: Any) -> Any:
        consultation_instances = get_consultation_queryset(
            self.context["request"].user
        ).filter(external_id__in=attrs["consultations"])

        if consultation_instances.count() != len(attrs["consultations"]):
            raise APIException(
                detail="You do not have access to one or more consultations"
            )

        attrs["consultations"] = consultation_instances
        return super().validate(attrs)


class TokenOnGenerateTokenSerializer(Serializer):
    class ResponseSerializer(Serializer):
        requestId = UUIDField()

    abhaAddress = CharField(max_length=50, required=True)
    linkToken = CharField(max_length=1000, required=True)
    response = ResponseSerializer(required=True)


class LinkOnCarecontextSerializer(Serializer):
    class ResponseSerializer(Serializer):
        requestId = UUIDField()

    abhaAddress = CharField(max_length=50, required=True)
    status = CharField(max_length=1000, required=True)
    response = ResponseSerializer(required=True)
