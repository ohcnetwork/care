import enum

from django.db import models

from care.facility.models import FacilityBaseModel
from care.facility.models.mixins.permissions.facility import FacilityRelatedPermissionMixin
from care.users.models import User


class PrescriptionSupplier(FacilityBaseModel):
    class SchemeEnum(enum.Enum):
        GOVERNMENT_SUPPLY = 10
        DONATION = 30
        PAID_BY_PATIENT = 40

    SchemeChoices = [(e.value, e.name) for e in SchemeEnum]

    class StatusEnum(enum.Enum):
        PENDING = 10
        INITIATED = 30
        COMPLETED = 40
        DEFERRED = 50

    StatusChoices = [(e.value, e.name) for e in StatusEnum]

    facility = models.ForeignKey("Facility", on_delete=models.PROTECT)
    consultation = models.ForeignKey(
        "PatientConsultation", on_delete=models.PROTECT, related_name="patient_consultation"
    )
    scheme = models.IntegerField(choices=SchemeChoices, default=10, null=False, blank=False)
    status = models.IntegerField(choices=StatusChoices, default=10, null=False, blank=False)
    supplier = models.TextField(default="", blank=True)
    remarks = models.TextField(default="", blank=True)
    updated_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def has_object_read_permission(self, request):
        return (
            request.user.is_superuser
            or (
                self.facility
                and request.user.user_type == User.TYPE_VALUE_MAP["Pharmacist"]
                and request.user in self.facility.users.all()
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (self.facility and request.user.district == self.facility.district)
            )
            or (
                request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
                and (self.facility and request.user.state == self.facility.state)
            )
        )

    def has_object_write_permission(self, request):
        if (
            request.user.user_type == User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]
            or request.user.user_type == User.TYPE_VALUE_MAP["StaffReadOnly"]
        ):
            return False
        return self.has_object_read_permission(request)
