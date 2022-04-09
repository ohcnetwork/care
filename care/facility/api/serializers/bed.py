from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, UUIDField

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.asset import AssetLocationSerializer, AssetSerializer
from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.bed import AssetBed, Bed, ConsultationBed
from care.facility.models.facility import Facility
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.queryset.facility import get_facility_queryset
from config.serializers import ChoiceField


class BedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    bed_type = ChoiceField(choices=Bed.BedTypeChoices)

    location_object = AssetLocationSerializer(source="location", read_only=True)

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


class AssetBedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    asset_object = AssetSerializer(source="asset", read_only=True)
    bed_object = BedSerializer(source="bed", read_only=True)

    asset = UUIDField(write_only=True, required=True)
    bed = UUIDField(write_only=True, required=True)

    class Meta:
        model = AssetBed
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        user = self.context["request"].user
        if "asset" in attrs and "bed" in attrs:
            asset = get_object_or_404(Asset.objects.filter(external_id=attrs["asset"]))
            bed = get_object_or_404(Bed.objects.filter(external_id=attrs["bed"]))
            facilities = get_facility_queryset(user)
            if (not facilities.filter(id=asset.current_location.facility.id).exists()) or (
                not facilities.filter(id=bed.facility.id).exists()
            ):
                raise PermissionError()
            attrs["asset"] = asset
            attrs["bed"] = bed
            if asset.current_location.facility.id != bed.facility.id:
                raise ValidationError({"asset": "Should be in the same facility as the bed"})
        else:
            raise ValidationError({"asset": "Field is Required", "bed": "Field is Required"})
        return super().validate(attrs)


class ConsultationBedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    consultation_object = PatientConsultationSerializer(source="consultation", read_only=True)
    bed_object = BedSerializer(source="bed", read_only=True)

    consultation = UUIDField(write_only=True, required=True)
    bed = UUIDField(write_only=True, required=True)

    class Meta:
        model = ConsultationBed
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        user = self.context["request"].user
        if "consultation" in attrs and "bed" in attrs:
            consultation = get_object_or_404(PatientConsultation.objects.filter(external_id=attrs["consultation"]))
            bed = get_object_or_404(Bed.objects.filter(external_id=attrs["bed"]))
            facilities = get_facility_queryset(user)
            if (not facilities.filter(id=consultation.facility.id).exists()) or (
                not facilities.filter(id=bed.facility.id).exists()
            ):
                raise PermissionError()
            attrs["consultation"] = consultation
            attrs["bed"] = bed
            if consultation.facility.id != bed.facility.id:
                raise ValidationError({"consultation": "Should be in the same facility as the bed"})
        else:
            raise ValidationError({"consultation": "Field is Required", "bed": "Field is Required"})
        return super().validate(attrs)
