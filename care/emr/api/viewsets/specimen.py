from rest_framework.exceptions import PermissionDenied

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin, EMRUpdateMixin
from care.emr.models.specimen import Specimen
from care.emr.resources.specimen.spec import (
    BaseSpecimenSpec,
    SpecimenReadSpec,
    SpecimenRetrieveSpec,
    SpecimenUpdateSpec,
)
from care.security.authorization.base import AuthorizationController


class SpecimenViewSet(EMRRetrieveMixin, EMRUpdateMixin, EMRBaseViewSet):
    database_model = Specimen
    pydantic_model = BaseSpecimenSpec
    pydantic_update_model = SpecimenUpdateSpec
    pydantic_read_model = SpecimenReadSpec
    pydantic_retrieve_model = SpecimenRetrieveSpec

    def authorize_update(self, request_obj, model_instance):
        service_request = model_instance.service_request
        if not AuthorizationController.call(
            "can_write_specimen",
            self.request.user,
            service_request,
        ):
            raise PermissionDenied("You do not have permission to write this specimen")

    def authorize_retrieve(self, model_instance):
        service_request = model_instance.service_request
        if not AuthorizationController.call(
            "can_read_specimen",
            self.request.user,
            service_request,
        ):
            raise PermissionDenied("You do not have permission to read this specimen")
