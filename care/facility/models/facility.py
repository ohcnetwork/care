from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _

from care.emr.models import FacilityOrganization
from care.emr.models.organization import FacilityOrganizationUser
from care.facility.models.facility_flag import FacilityFlag
from care.security.models import RoleModel
from care.security.roles.role import FACILITY_ADMIN_ROLE
from care.utils.models.base import BaseModel
from care.utils.models.choices import reverse_choices
from care.utils.models.validators import mobile_or_landline_number_validator

User = get_user_model()

class HubRelationship(IntegerChoices):
    REGULAR_HUB = 1, _("Regular Hub")
    TELE_ICU_HUB = 2, _("Tele ICU Hub")


class FacilityFeature(models.IntegerChoices):
    CT_SCAN_FACILITY = 1, "CT Scan Facility"
    MATERNITY_CARE = 2, "Maternity Care"
    X_RAY_FACILITY = 3, "X-Ray Facility"
    NEONATAL_CARE = 4, "Neonatal Care"
    OPERATION_THEATER = 5, "Operation Theater"
    BLOOD_BANK = 6, "Blood Bank"

FACILITY_TYPES = [
    (1, "Educational Inst"),
    (2, "Private Hospital"),
    (3, "Other"),
    (4, "Hostel"),
    (5, "Hotel"),
    (6, "Lodge"),
    (7, "TeleMedicine"),
    # 8, "Govt Hospital" # Change from "Govt Hospital" to "Govt Medical College Hospitals"
    (9, "Govt Labs"),
    (10, "Private Labs"),
    # Use 8xx for Govt owned hospitals and health centres
    (800, "Primary Health Centres"),
    # 801, "24x7 Public Health Centres" # Change from "24x7 Public Health Centres" to "Primary Health Centres"
    (802, "Family Health Centres"),
    (803, "Community Health Centres"),
    # 820, "Urban Primary Health Center" # Change from "Urban Primary Health Center" to "Primary Health Centres"
    (830, "Taluk Hospitals"),
    # 831, "Taluk Headquarters Hospitals" # Change from "Taluk Headquarters Hospitals" to "Taluk Hospitals"
    (840, "Women and Child Health Centres"),
    # 850, "General hospitals" # Change from "General hospitals" to "District Hospitals"
    (860, "District Hospitals"),
    (870, "Govt Medical College Hospitals"),
    (900, "Co-operative hospitals"),
    (910, "Autonomous healthcare facility"),
    # Use 9xx for Labs
    # 950, "Corona Testing Labs" # Change from "Corona Testing Labs" to "Govt Labs"
    # Use 10xx for Corona Care Center
    # 1000, "Corona Care Centre" # Change from "Corona Care Centre" to "Other"
    (1010, "COVID-19 Domiciliary Care Center"),
    # Use 11xx for First Line Treatment Centre
    (1100, "First Line Treatment Centre"),
    # Use 12xx for Second Line Treatment Center
    (1200, "Second Line Treatment Center"),
    # Use 13xx for Shifting Centers
    (1300, "Shifting Centre"),
    # Use 14xx for Covid Management Centers.
    (1400, "Covid Management Center"),
    # Use 15xx for Resource Management Centers.
    (1500, "Request Approving Center"),
    (1510, "Request Fulfilment Center"),
    # Use 16xx for War Rooms.
    (1600, "District War Room"),
    (3000, "Clinical Non Governmental Organization"),
    (3001, "Non Clinical Non Governmental Organization"),
    (4000, "Community Based Organization"),
]

REVERSE_FACILITY_TYPES = reverse_choices(FACILITY_TYPES)
REVERSE_REVERSE_FACILITY_TYPES = {v: k for k, v in REVERSE_FACILITY_TYPES.items()}

DOCTOR_TYPES = [
    (1, "General Medicine"),
    (2, "Pulmonology"),
    (3, "Intensivist"),
    (4, "Pediatrician"),
    (5, "Others"),
    (6, "Anesthesiologist"),
    (7, "Cardiac Surgeon"),
    (8, "Cardiologist"),
    (9, "Dentist"),
    (10, "Dermatologist"),
    (11, "Diabetologist"),
    (12, "Emergency Medicine Physician"),
    (13, "Endocrinologist"),
    (14, "Family Physician"),
    (15, "Gastroenterologist"),
    (16, "General Surgeon"),
    (17, "Geriatrician"),
    (18, "Hematologist"),
    (19, "Immunologist"),
    (20, "Infectious Disease Specialist"),
    (21, "MBBS doctor"),
    (22, "Medical Officer"),
    (23, "Nephrologist"),
    (24, "Neuro Surgeon"),
    (25, "Neurologist"),
    (26, "Obstetrician/Gynecologist (OB/GYN)"),
    (27, "Oncologist"),
    (28, "Oncology Surgeon"),
    (29, "Ophthalmologist"),
    (30, "Oral and Maxillofacial Surgeon"),
    (31, "Orthopedic"),
    (32, "Orthopedic Surgeon"),
    (33, "Otolaryngologist (ENT)"),
    (34, "Palliative care Physician"),
    (35, "Pathologist"),
    (36, "Pediatric Surgeon"),
    (37, "Physician"),
    (38, "Plastic Surgeon"),
    (39, "Psychiatrist"),
    (40, "Pulmonologist"),
    (41, "Radio technician"),
    (42, "Radiologist"),
    (43, "Rheumatologist"),
    (44, "Sports Medicine Specialist"),
    (45, "Thoraco-Vascular Surgeon"),
    (46, "Transfusion Medicine Specialist"),
    (47, "Urologist"),
    (48, "Nurse"),
    (49, "Allergist/Immunologist"),
    (50, "Cardiothoracic Surgeon"),
    (51, "Gynecologic Oncologist"),
    (52, "Hepatologist"),
    (53, "Internist"),
    (54, "Neonatologist"),
    (55, "Pain Management Specialist"),
    (56, "Physiatrist (Physical Medicine and Rehabilitation)"),
    (57, "Podiatrist"),
    (58, "Preventive Medicine Specialist"),
    (59, "Radiation Oncologist"),
    (60, "Sleep Medicine Specialist"),
    (61, "Transplant Surgeon"),
    (62, "Trauma Surgeon"),
    (63, "Vascular Surgeon"),
    (64, "Critical Care Physician"),
]



class Facility(BaseModel):
    name = models.CharField(max_length=1000, blank=False, null=False)
    description = models.TextField(blank=True, null=False)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    facility_type = models.IntegerField(choices=FACILITY_TYPES)
    features = ArrayField(
        models.SmallIntegerField(choices=FacilityFeature),
        blank=True,
        null=True,
    )
    longitude = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    latitude = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    pincode = models.IntegerField(default=None, null=True)
    address = models.TextField()

    geo_organization = models.ForeignKey(
        "emr.Organization", on_delete=models.SET_NULL, null=True, blank=True
    )
    geo_organization_cache = ArrayField(models.IntegerField(), default=list)

    default_internal_organization = models.ForeignKey(
        "emr.FacilityOrganization",
        on_delete=models.SET_NULL,
        related_name="default_facilities",
        null=True,
        blank=True,
    )
    internal_organization_cache = ArrayField(models.IntegerField(), default=list)

    phone_number = models.CharField(
        max_length=14, blank=True, validators=[mobile_or_landline_number_validator]
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    cover_image_url = models.CharField(
        blank=True, null=True, default=None, max_length=500
    )
    middleware_address = models.CharField(null=True, default=None, max_length=200)

    is_public = models.BooleanField(default=False)

    print_templates = models.JSONField(default=list)

    class Meta:
        verbose_name_plural = "Facilities"


    def read_cover_image_url(self):
        if self.cover_image_url:
            if settings.FACILITY_CDN:
                return f"{settings.FACILITY_CDN}/{self.cover_image_url}"
            return f"{settings.FACILITY_S3_BUCKET_EXTERNAL_ENDPOINT}/{settings.FACILITY_S3_BUCKET}/{self.cover_image_url}"
        return None

    def __str__(self):
        return f"{self.name}"

    def sync_cache(self):
        self.geo_organization_cache = []
        if self.geo_organization:
            self.geo_organization_cache = [
                *self.geo_organization.parent_cache,
                self.geo_organization.id,
            ]

        facility_organizations = FacilityOrganization.objects.filter(facility=self)
        cache = []
        for facility_organization in facility_organizations:
            cache = [
                *cache,
                *facility_organization.parent_cache,
                facility_organization.id,
            ]
        cache = list(set(cache))
        self.internal_organization_cache = cache
        super().save(
            update_fields=["geo_organization_cache", "internal_organization_cache"]
        )

    def save(self, *args, **kwargs) -> None:
        is_create = self.pk is None
        super().save(*args, **kwargs)

        if is_create:
            facility_organization = FacilityOrganization.objects.create(
                org_type="root",
                name="Administration",
                system_generated=True,
                facility=self,
            )
            self.default_internal_organization = facility_organization
            super().save(update_fields=["default_internal_organization"])
            FacilityOrganizationUser.objects.create(
                organization=facility_organization,
                user=self.created_by,
                role=RoleModel.objects.get_or_create(name=FACILITY_ADMIN_ROLE.name)[0],
            )
        self.sync_cache()

    def get_facility_flags(self):
        return FacilityFlag.get_all_flags(self.id)
