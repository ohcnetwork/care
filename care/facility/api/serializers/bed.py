from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    IntegerField,
    ListField,
    ModelSerializer,
    SerializerMethodField,
    UUIDField,
)

from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.api.serializers.asset import AssetLocationSerializer, AssetSerializer
from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.bed import (
    AssetBed,
    Bed,
    ConsultationBed,
    ConsultationBedAsset,
)
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_base import BedTypeChoices
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.queryset.consultation import get_consultation_queryset
from care.utils.queryset.facility import get_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField


class BedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    bed_type = ChoiceField(choices=BedTypeChoices)

    location_object = AssetLocationSerializer(source="location", read_only=True)
    is_occupied = BooleanField(default=False, read_only=True)

    location = UUIDField(write_only=True, required=True)
    facility = UUIDField(write_only=True, required=True)

    number_of_beds = IntegerField(required=False, default=1, write_only=True)

    def validate_number_of_beds(self, value):
        if value > 100:
            raise ValidationError("Cannot create more than 100 beds at once.")
        return value

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
            asset: Asset = get_object_or_404(
                Asset.objects.filter(external_id=attrs["asset"])
            )
            bed: Bed = get_object_or_404(Bed.objects.filter(external_id=attrs["bed"]))
            facilities = get_facility_queryset(user)
            if (
                not facilities.filter(id=asset.current_location.facility.id).exists()
            ) or (not facilities.filter(id=bed.facility.id).exists()):
                raise PermissionError()
            if asset.asset_class not in [
                AssetClasses.HL7MONITOR.name,
                AssetClasses.ONVIF.name,
            ]:
                raise ValidationError({"asset": "Asset is not a monitor or camera"})
            attrs["asset"] = asset
            attrs["bed"] = bed
            if asset.current_location.facility.id != bed.facility.id:
                raise ValidationError(
                    {"asset": "Should be in the same facility as the bed"}
                )
            if (
                asset.asset_class == AssetClasses.HL7MONITOR.name
                and AssetBed.objects.filter(
                    bed=bed, asset__asset_class=asset.asset_class
                ).exists()
            ):
                raise ValidationError(
                    {
                        "asset": "Bed is already in use by another asset of the same class"
                    }
                )
        else:
            raise ValidationError(
                {"asset": "Field is Required", "bed": "Field is Required"}
            )
        return super().validate(attrs)


class PatientAssetBedSerializer(ModelSerializer):
    asset = AssetSerializer(read_only=True)
    bed = BedSerializer(read_only=True)
    patient = SerializerMethodField()

    def get_patient(self, obj):
        from care.facility.api.serializers.patient import PatientListSerializer

        patient = PatientRegistration.objects.filter(
            last_consultation__current_bed__bed=obj.bed
        ).first()
        if patient:
            return PatientListSerializer(patient).data

    class Meta:
        model = AssetBed
        exclude = ("external_id", "id") + TIMESTAMP_FIELDS


class ConsultationBedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    bed_object = BedSerializer(source="bed", read_only=True)

    consultation = ExternalIdSerializerField(
        queryset=PatientConsultation.objects.all(), write_only=True, required=True
    )
    bed = ExternalIdSerializerField(
        queryset=Bed.objects.all(), write_only=True, required=True
    )

    assets = ListField(child=UUIDField(), required=False, write_only=True)
    assets_objects = AssetSerializer(source="assets", many=True, read_only=True)

    class Meta:
        model = ConsultationBed
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):
        user = self.context["request"].user
        if "consultation" in attrs and "bed" in attrs and "start_date" in attrs:
            bed = attrs["bed"]
            facilities = get_facility_queryset(user)
            if not facilities.filter(id=bed.facility_id).exists():
                raise PermissionError()

            permitted_consultations = get_consultation_queryset(user)
            consultation: PatientConsultation = get_object_or_404(
                permitted_consultations.filter(id=attrs["consultation"].id)
            )
            if not consultation.patient.is_active:
                raise ValidationError(
                    {"patient:": ["Patient is already discharged from CARE"]}
                )

            if consultation.facility_id != bed.facility_id:
                raise ValidationError(
                    {"consultation": "Should be in the same facility as the bed"}
                )

            previous_consultation_bed = consultation.current_bed
            if (
                previous_consultation_bed
                and previous_consultation_bed.bed == bed
                and set(
                    previous_consultation_bed.assets.order_by(
                        "external_id"
                    ).values_list("external_id", flat=True)
                )
                == set(attrs.get("assets", []))
            ):
                raise ValidationError(
                    {"consultation": "These set of bed and assets are already assigned"}
                )

            start_date = attrs["start_date"]
            end_date = attrs.get("end_date", None)

            qs = ConsultationBed.objects.filter(consultation=consultation)
            # Validations based of the latest entry
            if qs.exists():
                latest_qs = qs.latest("id")
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

            # Conflict checking logic
            existing_qs = ConsultationBed.objects.filter(bed=bed).exclude(
                consultation=consultation
            )
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

        with transaction.atomic():
            ConsultationBed.objects.filter(
                end_date__isnull=True, consultation=consultation
            ).update(end_date=validated_data["start_date"])
            if assets_ids := validated_data.pop("assets", None):
                assets = (
                    Asset.objects.annotate(
                        is_in_use=Exists(
                            ConsultationBedAsset.objects.filter(
                                Q(consultation_bed__end_date__gt=timezone.now())
                                | Q(consultation_bed__end_date__isnull=True),
                                asset=OuterRef("pk"),
                            )
                        )
                    )
                    .filter(
                        is_in_use=False,
                        external_id__in=assets_ids,
                        current_location__facility=consultation.facility_id,
                    )
                    .exclude(
                        asset_class__in=[
                            AssetClasses.HL7MONITOR.name,
                            AssetClasses.ONVIF.name,
                        ]
                    )
                    .values_list("external_id", flat=True)
                )
                not_found_assets = list(set(assets_ids) - set(assets))
                if not_found_assets:
                    raise ValidationError(
                        f"Some assets are not available - {' ,'.join(map(str, not_found_assets))}"
                    )
            obj: ConsultationBed = super().create(validated_data)
            if assets_ids:
                asset_objects = Asset.objects.filter(external_id__in=assets_ids).only(
                    "id"
                )
                ConsultationBedAsset.objects.bulk_create(
                    [
                        ConsultationBedAsset(consultation_bed=obj, asset=asset)
                        for asset in asset_objects
                    ]
                )

            consultation.current_bed = obj
            consultation.save(update_fields=["current_bed"])
            return obj

    def update(self, instance: ConsultationBed, validated_data) -> ConsultationBed:
        # assets once linked are not allowed to be changed
        validated_data.pop("assets", None)

        return super().update(instance, validated_data)
