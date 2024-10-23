from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    DateTimeField,
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
from care.utils.serializers.fields import ChoiceField, ExternalIdSerializerField


class BedSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    name = CharField(max_length=1024, required=True)
    bed_type = ChoiceField(choices=BedTypeChoices)

    location_object = AssetLocationSerializer(source="location", read_only=True)
    is_occupied = BooleanField(default=False, read_only=True)

    location = UUIDField(write_only=True, required=True)
    facility = UUIDField(write_only=True, required=True)

    number_of_beds = IntegerField(required=False, default=1, write_only=True)

    def validate_name(self, value):
        return value.strip() if value else value

    def validate_number_of_beds(self, value):
        max_beds = 100
        if value > max_beds:
            msg = f"Cannot create more than {max_beds} beds at once."
            raise ValidationError(msg)
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
                raise PermissionError
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
                raise PermissionError
            if AssetBed.objects.filter(asset=asset, bed=bed).exists():
                raise ValidationError(
                    {"non_field_errors": "Asset is already linked to bed"}
                )
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
            ) and AssetBed.objects.filter(
                bed=bed, asset__asset_class=asset.asset_class
            ).exists():
                raise ValidationError(
                    {"asset": "Another HL7 Monitor is already linked to this bed."}
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
        return None

    class Meta:
        model = AssetBed
        exclude = ("external_id", "id", *TIMESTAMP_FIELDS)


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
    start_date = DateTimeField(required=True)

    class Meta:
        model = ConsultationBed
        exclude = ("deleted", "external_id")
        read_only_fields = TIMESTAMP_FIELDS

    def validate(self, attrs):  # noqa: PLR0912
        if "consultation" not in attrs:
            raise ValidationError({"consultation": "This field is required."})
        if "bed" not in attrs:
            raise ValidationError({"bed": "This field is required."})
        if "start_date" not in attrs:
            raise ValidationError({"start_date": "This field is required."})

        user = self.context["request"].user
        bed = attrs["bed"]

        facilities = get_facility_queryset(user)
        if not facilities.filter(id=bed.facility_id).exists():
            msg = "You do not have access to this facility"
            raise ValidationError(msg)

        permitted_consultations = get_consultation_queryset(user).select_related(
            "patient"
        )
        consultation: PatientConsultation = get_object_or_404(
            permitted_consultations.filter(id=attrs["consultation"].id)
        )
        if (
            not consultation.patient.is_active
            or consultation.discharge_date
            or consultation.death_datetime
        ):
            msg = "Patient not active"
            raise ValidationError(msg)

        # bed validations
        if consultation.facility_id != bed.facility_id:
            msg = "Consultation and bed are not in the same facility"
            raise ValidationError(msg)
        if (
            ConsultationBed.objects.filter(bed=bed, end_date__isnull=True)
            .exclude(consultation=consultation)
            .exists()
        ):
            msg = "Bed is already in use"
            raise ValidationError(msg)

        # check whether the same set of bed and assets are already assigned
        current_consultation_bed = consultation.current_bed
        if (
            not self.instance
            and current_consultation_bed
            and current_consultation_bed.bed == bed
            and set(
                current_consultation_bed.assets.order_by("external_id").values_list(
                    "external_id", flat=True
                )
            )
            == set(attrs.get("assets", []))
        ):
            msg = "These set of bed and assets are already assigned"
            raise ValidationError(msg)

        # date validations
        # note: end_date is for setting end date on current instance
        current_start_date = attrs["start_date"]
        current_end_date = attrs.get("end_date", None)
        if current_end_date and current_end_date < current_start_date:
            raise ValidationError(
                {"end_date": "End date cannot be before the start date"}
            )
        if consultation.encounter_date > current_start_date:
            raise ValidationError(
                {"start_date": "Start date cannot be before the admission date"}
            )

        # validations based on patients previous consultation bed
        last_consultation_bed = (
            ConsultationBed.objects.filter(consultation=consultation)
            .exclude(id=self.instance.id if self.instance else None)
            .order_by("id")
            .last()
        )
        if (
            last_consultation_bed
            and current_start_date < last_consultation_bed.start_date
        ):
            raise ValidationError(
                {"start_date": "Start date cannot be before previous bed start date"}
            )

        # check bed occupancy conflicts
        if (
            not self.instance
            and current_consultation_bed
            and ConsultationBed.objects.filter(
                Q(bed=current_consultation_bed.bed),
                Q(start_date__gte=current_consultation_bed.start_date),
                Q(start_date__lte=current_start_date),
            )
            .exclude(id=current_consultation_bed.id)
            .exists()
        ):
            # validation for setting end date on current bed based on new bed start date
            raise ValidationError({"start_date": "Cannot create conflicting entry"})

        conflicting_beds = ConsultationBed.objects.filter(bed=bed)
        if conflicting_beds.filter(
            start_date__lte=current_start_date, end_date__gte=current_start_date
        ).exists():
            raise ValidationError({"start_date": "Cannot create conflicting entry"})
        if (
            current_end_date
            and conflicting_beds.filter(
                start_date__lte=current_end_date, end_date__gte=current_end_date
            ).exists()
        ):
            raise ValidationError({"end_date": "Cannot create conflicting entry"})
        return super().validate(attrs)

    def create(self, validated_data) -> ConsultationBed:
        consultation = validated_data["consultation"]
        with transaction.atomic():
            ConsultationBed.objects.filter(
                end_date__isnull=True, consultation=consultation
            ).update(end_date=validated_data["start_date"])
            if assets_ids := validated_data.pop("assets", None):
                # we check assets in use here as they might have been in use in
                # the previous bed
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
                not_found_assets = set(assets_ids) - set(assets)
                if not_found_assets:
                    msg = (
                        "Some assets are not available - "
                        f"{' ,'.join([str(x) for x in not_found_assets])}"
                    )
                    raise ValidationError(msg)
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
