from enum import Enum

from care.security.permissions.account import AccountPermissions
from care.security.permissions.activity_definition import ActivityDefinitionPermissions
from care.security.permissions.charge_item import ChargeItemPermissions
from care.security.permissions.charge_item_definition import (
    ChargeItemDefinitionPermissions,
)
from care.security.permissions.device import DevicePermissions
from care.security.permissions.diagnostic_report import DiagnosticReportPermissions
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.facility import FacilityPermissions
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.security.permissions.healthcare_service import HealthcareServicePermissions
from care.security.permissions.inventory_item import InventoryItemPermissions
from care.security.permissions.invoice import InvoicePermissions
from care.security.permissions.location import FacilityLocationPermissions
from care.security.permissions.medication import MedicationPermissions
from care.security.permissions.observation_definition import (
    ObservationDefinitionPermissions,
)
from care.security.permissions.organization import OrganizationPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.patient_identifier_config import (
    PatientIdentifierConfigPermissions,
)
from care.security.permissions.payment_reconciliation import (
    PaymentReconciliationPermissions,
)
from care.security.permissions.product import ProductPermissions
from care.security.permissions.product_knowledge import ProductKnowledgePermissions
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.security.permissions.resource_category import ResourceCategoryPermissions
from care.security.permissions.schedule import SchedulePermissions
from care.security.permissions.service_request import ServiceRequestPermissions
from care.security.permissions.specimen import SpecimenPermissions
from care.security.permissions.specimen_definition import SpecimenDefinitionPermissions
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions
from care.security.permissions.supply_request import SupplyRequestPermissions
from care.security.permissions.tag_config import TagConfigPermissions
from care.security.permissions.token import TokenPermissions
from care.security.permissions.user import UserPermissions
from care.security.permissions.user_schedule import UserSchedulePermissions


class PermissionHandler:
    pass


class PermissionController:
    """
    This class defines all permissions used within care.
    This class is used to abstract all operations related to permissions
    """

    override_permission_handlers = []
    # Override Permission Controllers will be defined from plugs

    internal_permission_handlers = [
        FacilityPermissions,
        QuestionnairePermissions,
        OrganizationPermissions,
        FacilityOrganizationPermissions,
        EncounterPermissions,
        PatientPermissions,
        UserPermissions,
        UserSchedulePermissions,
        FacilityLocationPermissions,
        ObservationDefinitionPermissions,
        DevicePermissions,
        SpecimenDefinitionPermissions,
        ActivityDefinitionPermissions,
        ServiceRequestPermissions,
        HealthcareServicePermissions,
        SpecimenPermissions,
        DiagnosticReportPermissions,
        ChargeItemDefinitionPermissions,
        ChargeItemPermissions,
        AccountPermissions,
        PaymentReconciliationPermissions,
        InvoicePermissions,
        MedicationPermissions,
        ProductKnowledgePermissions,
        ProductPermissions,
        SupplyDeliveryPermissions,
        SupplyRequestPermissions,
        InventoryItemPermissions,
        TagConfigPermissions,
        PatientIdentifierConfigPermissions,
        MedicationPermissions,
        TokenPermissions,
        SchedulePermissions,
        ResourceCategoryPermissions,
    ]

    cache = {}

    @classmethod
    def build_cache(cls):
        """
        Iterate through the entire permission library and create a list of permissions and associated Metadata
        """
        for handler in (
            cls.internal_permission_handlers + cls.override_permission_handlers
        ):
            for permission in handler:
                cls.cache[permission.name] = permission.value

    @classmethod
    def get_permissions(cls):
        if not cls.cache:
            cls.build_cache()
        return cls.cache

    @classmethod
    def get_enum(cls):
        if not cls.cache:
            cls.build_cache()

        return Enum("PermissionEnum", {name: name for name in cls.cache}, type=str)

    @classmethod
    def register_permission_handler(cls, handler):
        if handler not in cls.override_permission_handlers:
            cls.override_permission_handlers.append(handler)
