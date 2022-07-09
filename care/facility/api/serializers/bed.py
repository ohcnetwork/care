from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, UUIDField

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.asset import AssetLocationSerializer, AssetSerializer
from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.bed import AssetBed, Bed, ConsultationBed
from care.facility.models.facility import Facility
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.queryset.consultation import get_consultation_queryset
from care.utils.queryset.facility import get_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField
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
            location = get_object_or_404(
                AssetLocation.objects.filter(external_id=attrs["location"])
            )
            facility = get_object_or_404(
                Facility.objects.filter(external_id=attrs["facility"])
            )
            facilities = get_facility_queryset(user)
            if (not facilities.filter(id=location.facility.id).exists()) or (
                not facilities.filter(id=facility.id).exists()
            ):
                raise PermissionError()
            del attrs["location"]
            attrs["location"] = location
            attrs["facility"] = facility
        else:
            raise ValidationError(
                {"location": "Field is Required", "facility": "Field is Required"}
            )
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
            if (
                not facilities.filter(id=asset.current_location.facility.id).exists()
            ) or (not facilities.filter(id=bed.facility.id).exists()):
                raise PermissionError()
            attrs["asset"] = asset
            attrs["bed"] = bed
            if asset.current_location.facility.id != bed.facility.id:
                raise ValidationError(
                    {"asset": "Should be in the same facility as the bed"}
                )
        else:
            raise ValidationError(
                {"asset": "Field is Required", "bed": "Field is Required"}
            )
        return super().validate(attrs)


class ConsultationBedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    bed_object = BedSerializer(source="bed", read_only=True)

    consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), write_only=True, required=True
    )
    bed = ExternalIdSerializerField(
        queryset=Bed.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = ConsultationBed
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        user = self.context["request"].user
        if "consultation" in attrs and "bed" in attrs and "start_date" in attrs:
            bed = attrs["bed"]
            facilities = get_facility_queryset(user)
            permitted_consultations = get_consultation_queryset(user)
            consultation = get_object_or_404(
                permitted_consultations.filter(id=attrs["consultation"].id)
            )
            if not facilities.filter(id=bed.facility.id).exists():
                raise PermissionError()
            if consultation.facility.id != bed.facility.id:
                raise ValidationError(
                    {"consultation": "Should be in the same facility as the bed"}
                )
            start_date = attrs["start_date"]
            end_date = attrs.get("end_date", None)
            existing_qs = ConsultationBed.objects.filter(
                consultation=consultation, bed=bed
            )
            qs = ConsultationBed.objects.filter(consultation=consultation)
            # Validations based of the latest entry
            if qs.exists():
                latest_qs = qs.latest("id")
                if latest_qs.bed == bed:
                    raise ValidationError({"bed": "Bed is already in use"})
                if start_date < latest_qs.start_date:
                    raise ValidationError(
                        {
                            "start_date": "Start date cannot be before the latest start date"
                        }
                    )
                if end_date and end_date < latest_qs.start_date:
                    raise ValidationError(
                        {"end_date": "End date cannot be before the latest start date"}
                    )
            existing_qs = ConsultationBed.objects.filter(consultation=consultation)
            # Conflict checking logic
            if existing_qs.filter(start_date__gt=start_date).exists():
                raise ValidationError({"start_date": "Cannot create conflicting entry"})
            if end_date:
                if existing_qs.filter(
                    start_date__gt=end_date, end_date__lt=end_date
                ).exists():
                    raise ValidationError(
                        {"end_date": "Cannot create conflicting entry"}
                    )
        else:
            raise ValidationError(
                {
                    "consultation": "Field is Required",
                    "bed": "Field is Required",
                    "start_date": "Field is Required",
                }
            )
        return super().validate(attrs)

    def create(self, validated_data):
        consultation = validated_data["consultation"]
        bed = validated_data["bed"]

        if not consultation.patient.is_active:
            raise ValidationError(
                {"patient:": ["Patient is already discharged from CARE"]}
            )

        occupied_beds = ConsultationBed.objects.filter(end_date__isnull=True)

        if occupied_beds.filter(bed=bed).exists():
            raise ValidationError({"bed:": ["Bed already in use by patient"]})

        occupied_beds.filter(consultation=consultation).update(
            end_date=validated_data["start_date"]
        )

        # This needs better logic, when an update occurs and the latest bed is no longer the last bed consultation relation added.
        obj = super().create(validated_data)
        consultation.current_bed = obj
        consultation.save(update_fields=["current_bed"])
        return obj
