from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from care.facility.models import PatientExternalTest
from care.users.models import District, Ward, LocalBody, REVERSE_LOCAL_BODY_CHOICES
from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
    WardSerializer,
)


class PatientExternalTestSerializer(serializers.ModelSerializer):
    ward_object = WardSerializer(source="ward", read_only=True)
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)

    local_body_type = serializers.CharField(required=False, write_only=True)

    sample_collection_date = serializers.DateField(
        input_formats=["%Y-%m-%d"], required=False
    )
    result_date = serializers.DateField(input_formats=["%Y-%m-%d"], required=False)

    def validate_empty_values(self, data, *args, **kwargs):
        # if "is_repeat" in data:
        #     is_repeat = data["is_repeat"]
        #     if is_repeat.lower() == "yes":
        #         data["is_repeat"] = True
        #     else:
        #         data["is_repeat"] = False
        print(data)
        district_obj = None
        if "district" in data:
            district = data["district"]
            district_obj = District.objects.filter(name__icontains=district).first()
            if district_obj:
                data["district"] = district_obj.id
            else:
                raise ValidationError({"district": ["District Does not Exist"]})
        else:
            raise ValidationError({"district": ["District Not Present in Data"]})

        if "local_body_type" not in data:
            raise ValidationError(
                {"local_body_type": ["local_body_type is not present in data"]}
            )

        if not data["local_body_type"]:
            raise ValidationError(
                {"local_body_type": ["local_body_type cannot be empty"]}
            )

        if data["local_body_type"].lower() not in REVERSE_LOCAL_BODY_CHOICES:
            raise ValidationError({"local_body_type": ["Invalid Local Body Type"]})

        local_body_type = REVERSE_LOCAL_BODY_CHOICES[data["local_body_type"].lower()]

        local_body_obj = None
        if "local_body" in data and district_obj:
            if not data["local_body"]:
                raise ValidationError({"local_body": ["Local Body Cannot Be Empty"]})
            local_body = data["local_body"]
            local_body_obj = LocalBody.objects.filter(
                name__icontains=local_body,
                district=district_obj,
                body_type=local_body_type,
            ).first()
            if local_body_obj:
                data["local_body"] = local_body_obj.id
            else:
                raise ValidationError({"local_body": ["Local Body Does not Exist"]})
        else:
            raise ValidationError({"local_body": ["Local Body Not Present in Data"]})

        if "ward" in data and local_body_obj:
            try:
                int(data["ward"])
            except Exception:
                raise ValidationError({"ward": ["Ward must be an integer value"]})
            if data["ward"]:
                ward_obj = Ward.objects.filter(
                    number=data["ward"], local_body=local_body_obj
                ).first()
                if ward_obj:
                    data["ward"] = ward_obj.id
                else:
                    raise ValidationError({"ward": ["Ward Does not Exist"]})

        del data["local_body_type"]

        return super().validate_empty_values(data, *args, **kwargs)

    # def validate_ward(self, value):
    #     print(value)

    class Meta:
        model = PatientExternalTest
        fields = "__all__"

