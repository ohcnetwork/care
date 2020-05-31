from django.db.models import F

from django_filters import rest_framework as filters

from rest_framework import (
    filters as rest_filters,
    generics as rest_generics,
    mixins as rest_mixins,
    permissions as rest_permissions,
    status as rest_status,
    viewsets as rest_viewsets,
)
from apps.commons import (
    constants as commons_constants,
    filters as commons_filters,
    pagination as commons_pagination,
)
from apps.patients import (
    constants as patients_constants,
    models as patient_models,
    serializers as patient_serializers,
    filters as patients_filters,
)
from apps.facility import models as facility_models


class PatientViewSet(rest_viewsets.ModelViewSet):

    serializer_class = patient_serializers.PatientListSerializer
    pagination_class = commons_pagination.CustomPagination
    filter_backends = (
        filters.DjangoFilterBackend,
        rest_filters.OrderingFilter,
    )
    filterset_class = patients_filters.PatientFilter
    ordering_fields = (
        "name",
        "icmr_id",
        "govt_id",
        "facility",
        "year",
    )

    def retrieve(self, request, *args, **kwargs):
        self.serializer_class = patient_serializers.PatientDetailsSerializer
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        queryset = patient_models.Patient.objects.all()
        if (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.PORTEA
        ):
            queryset = queryset.filter(patient_status=patients_constants.HOME_ISOLATION)
        elif (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.FACILITY_MANAGER
        ):
            facility_ids = list(
                facility_models.FacilityUser.objects.filter(
                    user_id=self.request.user.id
                ).values_list("facility_id", flat=True)
            )
            queryset = queryset.filter(patientfacility__facility_id__in=facility_ids)
        return queryset.annotate(
            facility_status=F("patientfacility__patient_status__name"),
            facility_name=F("patientfacility__facility__name"),
            facility_type=F("patientfacility__facility__facility_type__name"),
            ownership_type=F("patientfacility__facility__owned_by__name"),
            facility_district=F("patientfacility__facility__district__name"),
        )


class PatientGroupViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.PatientGroup.objects.all()
    serializer_class = patient_serializers.PatientGroupSerializer


class CovidStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.CovidStatus.objects.all()
    serializer_class = patient_serializers.CovidStatusSerializer


class ClinicalStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.ClinicalStatus.objects.all()
    serializer_class = patient_serializers.ClinicalStatusSerializer


class PatientStatusViewSet(rest_viewsets.ModelViewSet):

    queryset = patient_models.PatientStatus.objects.all()
    serializer_class = patient_serializers.PatientStatusSerializer


class PatientTimeLineViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    ViewSet for Patient Timeline List
    """

    serializer_class = patient_serializers.PatientTimeLineSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = patients_filters.PatientTimelineFilter
    pagination_class = commons_pagination.CustomPagination

    def get_queryset(self):
        queryset = patient_models.PatientTimeLine.objects.filter(
            patient_id=self.kwargs.get("patient_id")
        )
        if (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.PORTEA
        ):
            queryset = queryset.filter(
                patient__patient_status=patients_constants.HOME_ISOLATION
            )
        elif (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.FACILITY_MANAGER
        ):
            facility_ids = list(
                facility_models.FacilityUser.objects.filter(
                    user_id=self.request.user.id
                ).values_list("facility_id", flat=True)
            )
            queryset = queryset.filter(
                patient__patientfacility__facility_id__in=facility_ids
            )
        return queryset


class PortieCallingDetailViewSet(
    rest_mixins.CreateModelMixin,
    rest_mixins.UpdateModelMixin,
    rest_viewsets.GenericViewSet,
):
    """
    views for create and update portie calling detail
    """

    serializer_class = patient_serializers.PortieCallingDetailSerialzier

    def get_queryset(self):
        queryset = patient_models.PortieCallingDetail.objects.all()
        if (
            self.request.user.user_type
            and self.request.user.user_type == commons_constants.FACILITY_MANAGER
        ):
            facility_ids = list(
                facility_models.FacilityUser.objects.filter(
                    user_id=self.request.user.id
                ).values_list("facility_id", flat=True)
            )
            queryset = queryset.filter(
                patient__patientfacility__facility_id__in=facility_ids
            )
        return queryset


class PatientSampleTestViewSet(
    rest_mixins.CreateModelMixin,
    rest_mixins.UpdateModelMixin,
    rest_viewsets.GenericViewSet,
):
    """
    views for create and update patient sample test
    """

    queryset = patient_models.PatientSampleTest.objects.all()
    serializer_class = patient_serializers.PatientSampleTestSerializer


class PatientTransferViewSet(
    rest_mixins.ListModelMixin,
    rest_mixins.UpdateModelMixin,
    rest_viewsets.GenericViewSet,
):
    """
    ViewSet for Patient Transfer List
    """

    http_method_names = ("patch", "get")
    queryset = patient_models.PatientTransfer.objects.all()
    serializer_class = patient_serializers.PatientTransferSerializer
    permission_classes = (rest_permissions.IsAuthenticated,)
    pagination_class = commons_pagination.CustomPagination
    filter_backends = (
        filters.DjangoFilterBackend,
        commons_filters.ReplaceFieldsOrderingFilter,
        rest_filters.SearchFilter,
    )
    filterset_class = patients_filters.PatientTransferFilter
    search_fields = (
        "^from_patient_facility__patient__icmr_id",
        "^from_patient_facility__patient__govt_id",
        "^from_patient_facility__facility__name",
        "^to_facility__name",
    )
    ordering_fields = (
        "icmr_id",
        "govt_id",
    )
    related_ordering_fields_map = {
        "icmr_id": "from_patient_facility__patient__icmr_id",
        "govt_id": "from_patient_facility__patient__govt_id",
        "patient_name": "from_patient_facility__patient__name",
        "gender": "from_patient_facility__patient__gender",
        "month": "from_patient_facility__patient__month",
        "year": "from_patient_facility__patient__year",
        "phone_number": "from_patient_facility__patient__phone_number",
    }

    def get_serializer_class(self):
        if self.action == "partial_update":
            return patient_serializers.PatientTransferUpdateSerializer
        return self.serializer_class
