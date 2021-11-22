from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, UUIDField

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.asset import AssetLocationSerializer
from care.facility.models.asset import AssetLocation
from care.facility.models.bed import Bed
from care.facility.models.facility import Facility
from care.utils.queryset.facility import get_facility_queryset
from config.serializers import ChoiceField


class BedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    bed_type = ChoiceField(choices=Bed.BedTypeChoices)

    location = AssetLocationSerializer(source="location", read_only=True)

    location = UUIDField(write_only=True, required=True)
    facility = UUIDField(write_only=True, required=True)

    class Meta:
        model = Bed
        exclude = ("deleted", "external_id", "assets")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):

        user = self.context["request"].user
        if "location" in attrs and "facility" in attrs:
            location = get_object_or_404(AssetLocation.objects.filter(external_id=attrs["location"]))
            facility = get_object_or_404(Facility.objects.filter(external_id=attrs["facility"]))
            facilities = get_facility_queryset(user)
            if (not facilities.filter(id=location.facility.id).exists()) or (
                not facilities.filter(id=facility.id).exists()
            ):
                raise PermissionError()
            del attrs["location"]
            attrs["location"] = location
            attrs["facility"] = facility
        else:
            raise ValidationError({"location": "Field is Required", "facility": "Field is Required"})
        return super().validate(attrs)
