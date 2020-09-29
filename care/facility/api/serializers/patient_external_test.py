from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models import PatientExternalTest
from care.users.models import Ward, LocalBody
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer, WardSerializer


class PatientExternalTestSerializer(serializers.ModelSerializer):
    ward_object = WardSerializer(source="ward", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)

    sample_collection_date = serializers.DateTimeField(input_formats=["%d-%m-%Y %H:%M"])
    result_date = serializers.DateTimeField(input_formats=["%d-%m-%Y %H:%M"])

    def validate_empty_values(self, data, *args, **kwargs):
        if "is_repeat" in data:
            is_repeat = data["is_repeat"]
            if is_repeat.lower() == "yes":
                data["is_repeat"] = True
            else:
                data["is_repeat"] = False
        if "ward" in data:
            if data["ward"]:
                ward_obj = Ward.objects.filter(name__icontains=data["ward"]).first()
                if ward_obj:
                    data["ward"] = ward_obj.id
                else:
                    raise ValidationError({"ward": ["Ward Does not Exist"]})
        local_body = data["local_body"]
        local_body_obj = LocalBody.objects.filter(name__icontains=local_body).first()
        if local_body_obj:
            data["local_body"] = local_body_obj.id
        else:
            raise ValidationError({"local_body": ["Local Body Does not Exist"]})

        return super().validate_empty_values(data, *args, **kwargs)

    # def validate_ward(self, value):
    #     print(value)

    class Meta:
        model = PatientExternalTest
        fields = "__all__"

