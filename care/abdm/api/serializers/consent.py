from rest_framework import serializers

from care.abdm.api.serializers.abha_number import AbhaNumberSerializer
from care.abdm.models.consent import ConsentArtefact, ConsentRequest
from care.users.api.serializers.user import UserBaseMinimumSerializer


class ConsentArtefactSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)

    class Meta:
        model = ConsentArtefact
        exclude = (
            "deleted",
            "external_id",
            "key_material_private_key",
            "key_material_public_key",
            "key_material_nonce",
            "key_material_algorithm",
            "key_material_curve",
            "signature",
        )


class ConsentRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id", read_only=True)
    patient_abha_object = AbhaNumberSerializer(source="patient_abha", read_only=True)
    requester = UserBaseMinimumSerializer(read_only=True)
    consent_artefacts = ConsentArtefactSerializer(many=True, read_only=True)

    class Meta:
        model = ConsentRequest
        exclude = ("deleted", "external_id")
