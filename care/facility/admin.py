from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from djangoql.admin import DjangoQLSearchMixin
from djqscsv import render_to_csv_response

from care.facility.models.ambulance import Ambulance, AmbulanceDriver
from care.facility.models.asset import Asset
from care.facility.models.bed import AssetBed, Bed, ConsultationBed
from care.facility.models.facility import FacilityHubSpoke
from care.facility.models.file_upload import FileUpload
from care.facility.models.patient_consultation import (
    PatientConsent,
    PatientConsultation,
)
from care.facility.models.patient_sample import PatientSample
from care.utils.registries.feature_flag import FlagRegistry, FlagType

from .models import (
    Building,
    Disease,
    Facility,
    FacilityCapacity,
    FacilityFlag,
    FacilityInventoryItem,
    FacilityInventoryItemTag,
    FacilityInventoryUnit,
    FacilityInventoryUnitConverter,
    FacilityStaff,
    FacilityUser,
    FacilityVolunteer,
    Inventory,
    InventoryItem,
    InventoryLog,
    PatientExternalTest,
    PatientInvestigation,
    PatientInvestigationGroup,
    PatientRegistration,
    Room,
    StaffRoomAllocation,
)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    search_fields = ["name"]


class DistrictFilter(SimpleListFilter):
    """DistrictFilter"""

    title = "District"
    parameter_name = "district"

    def lookups(self, request, model_admin):
        district = Facility.objects.values_list("district__name", flat=True)
        return [(x, x) for x in set(district)]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(district__name=self.value())


class StateFilter(SimpleListFilter):
    """State filter"""

    title = "State"
    parameter_name = "state"

    def lookups(self, request, model_admin):
        state = Facility.objects.values_list("state__name", flat=True)
        return [(x, x) for x in set(state)]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(state__name=self.value())


@admin.register(Facility)
class FacilityAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    search_fields = ["name"]
    list_filter = [StateFilter, DistrictFilter]
    djangoql_completion_enabled_by_default = True


@admin.register(FacilityHubSpoke)
class FacilityHubSpokeAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    search_fields = ["name"]
    djangoql_completion_enabled_by_default = True


@admin.register(FacilityStaff)
class FacilityStaffAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "staff"]
    djangoql_completion_enabled_by_default = True


@admin.register(FacilityCapacity)
class FacilityCapacityAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility"]
    djangoql_completion_enabled_by_default = True


@admin.register(FacilityVolunteer)
class FacilityVolunteerAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "volunteer"]
    djangoql_completion_enabled_by_default = True


@admin.register(Inventory)
class InventoryAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["facility", "item"]
    djangoql_completion_enabled_by_default = True


@admin.register(InventoryItem)
class InventoryItemAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    search_fields = ["name", "description"]
    djangoql_completion_enabled_by_default = True


@admin.register(Room)
class RoomAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["building"]
    search_fields = ["building", "num"]
    djangoql_completion_enabled_by_default = True


@admin.register(StaffRoomAllocation)
class StaffRoomAllocationAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["staff", "room"]
    djangoql_completion_enabled_by_default = True


class AmbulanceDriverInline(DjangoQLSearchMixin, admin.TabularInline):
    model = AmbulanceDriver
    djangoql_completion_enabled_by_default = True


@admin.register(Ambulance)
class AmbulanceAdmin(admin.ModelAdmin):
    search_fields = ["vehicle_number"]
    inlines = [
        AmbulanceDriverInline,
    ]
    djangoql_completion_enabled_by_default = True


@admin.register(AmbulanceDriver)
class AmbulanceDriverAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    autocomplete_fields = ["ambulance"]
    djangoql_completion_enabled_by_default = True


@admin.register(PatientRegistration)
class PatientAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "name", "year_of_birth", "gender")
    djangoql_completion_enabled_by_default = True


@admin.register(PatientSample)
class PatientSampleAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    djangoql_completion_enabled_by_default = True


@admin.register(PatientExternalTest)
class PatientExternalTestAdmin(admin.ModelAdmin):
    pass


@admin.register(PatientInvestigation)
class PatientTestAdmin(admin.ModelAdmin):
    pass


@admin.register(PatientInvestigationGroup)
class PatientTestGroupAdmin(admin.ModelAdmin):
    pass


class ExportCsvMixin:
    @admin.action(description="Export Selected")
    def export_as_csv(self, request, queryset):
        queryset = FacilityUser.objects.all().values(*FacilityUser.CSV_MAPPING.keys())
        return render_to_csv_response(
            queryset,
            field_header_map=FacilityUser.CSV_MAPPING,
            field_serializer_map=FacilityUser.CSV_MAKE_PRETTY,
        )


@admin.register(FacilityUser)
class FacilityUserAdmin(DjangoQLSearchMixin, admin.ModelAdmin, ExportCsvMixin):
    djangoql_completion_enabled_by_default = True
    actions = ["export_as_csv"]


@admin.register(FacilityFlag)
class FacilityFlagAdmin(admin.ModelAdmin):
    class FacilityFeatureFlagForm(forms.ModelForm):
        flag = forms.ChoiceField(
            choices=lambda: FlagRegistry.get_all_flags_as_choices(FlagType.FACILITY)
        )

        class Meta:
            fields = ("flag", "facility")
            model = FacilityFlag

    form = FacilityFeatureFlagForm


admin.site.register(InventoryLog)
admin.site.register(Disease)
admin.site.register(FacilityInventoryUnit)
admin.site.register(FacilityInventoryUnitConverter)
admin.site.register(FacilityInventoryItem)
admin.site.register(FacilityInventoryItemTag)
admin.site.register(AssetBed)
admin.site.register(Asset)
admin.site.register(Bed)
admin.site.register(ConsultationBed)
admin.site.register(PatientConsent)
admin.site.register(FileUpload)
admin.site.register(PatientConsultation)
