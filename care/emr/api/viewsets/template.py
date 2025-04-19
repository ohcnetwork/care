from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.resources.template.spec import (
    FacilityReportTemplateCreateSpec,
    FacilityReportTemplateReadSpec,
    FacilityReportTemplateRetrieveSpec,
    FacilityReportTemplateUpdateSpec,
)
from care.facility.models import FacilityReportTemplate


class FacilityReportTemplateViewSet(EMRModelViewSet):
    database_model = FacilityReportTemplate
    pydantic_model = FacilityReportTemplateCreateSpec
    pydantic_read_model = FacilityReportTemplateReadSpec
    pydantic_update_model = FacilityReportTemplateUpdateSpec
    pydantic_retrieve_model = FacilityReportTemplateRetrieveSpec
