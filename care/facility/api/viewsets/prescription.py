from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissions
from redis_om import FindQuery
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from care.facility.api.serializers.prescription import (
    MedicineAdministrationSerializer,
    PrescriptionSerializer,
)
from care.facility.models import (
    MedicineAdministration,
    Prescription,
    PrescriptionDosageType,
    PrescriptionType,
    generate_choices,
)
from care.facility.static_data.medibase import MedibaseMedicine
from care.utils.filters.choicefilter import CareChoiceFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.queryset.consultation import get_consultation_queryset
from care.utils.static_data.helpers import query_builder, token_escaper


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


inverse_prescription_type = inverse_choices(generate_choices(PrescriptionType))
inverse_prescription_dosage_type = inverse_choices(
    generate_choices(PrescriptionDosageType)
)


class MedicineAdminstrationFilter(filters.FilterSet):
    prescription = filters.UUIDFilter(field_name="prescription__external_id")
    administered_date = filters.DateFromToRangeFilter(field_name="administered_date")
    archived = filters.BooleanFilter(method="archived_filter")

    def archived_filter(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.exclude(archived_on__isnull=value)


class MedicineAdministrationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    serializer_class = MedicineAdministrationSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = MedicineAdministration.objects.all().order_by("-created_date")
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = MedicineAdminstrationFilter

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        consultation_obj = self.get_consultation_obj()
        return self.queryset.filter(prescription__consultation_id=consultation_obj.id)

    @extend_schema(tags=["prescription_administration"])
    @action(methods=["POST"], detail=True)
    def archive(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.archived_on:
            return Response(
                {"error": "Already Archived"}, status=status.HTTP_400_BAD_REQUEST
            )
        instance.archived_by = request.user
        instance.archived_on = timezone.now()
        instance.save()
        return Response({}, status=status.HTTP_200_OK)


class ConsultationPrescriptionFilter(filters.FilterSet):
    dosage_type = MultiSelectFilter()
    prescription_type = CareChoiceFilter(choice_dict=inverse_prescription_type)
    discontinued = filters.BooleanFilter()


class ConsultationPrescriptionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = PrescriptionSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = Prescription.objects.all().order_by("-created_date")
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ConsultationPrescriptionFilter

    def get_consultation_obj(self):
        return get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )

    def get_queryset(self):
        consultation_obj = self.get_consultation_obj()
        return self.queryset.filter(consultation_id=consultation_obj.id)

    def perform_create(self, serializer):
        consultation_obj = self.get_consultation_obj()
        serializer.save(prescribed_by=self.request.user, consultation=consultation_obj)

    @extend_schema(tags=["prescriptions"])
    @action(
        methods=["POST"],
        detail=True,
    )
    def discontinue(self, request, *args, **kwargs):
        prescription_obj = self.get_object()
        prescription_obj.discontinued = True
        prescription_obj.discontinued_reason = request.data.get(
            "discontinued_reason", None
        )
        prescription_obj.save()
        return Response({}, status=status.HTTP_200_OK)

    @extend_schema(tags=["prescriptions"])
    @action(
        methods=["POST"],
        detail=True,
        serializer_class=MedicineAdministrationSerializer,
    )
    def administer(self, request, *args, **kwargs):
        prescription_obj = self.get_object()
        if prescription_obj.discontinued:
            return Response(
                {"error": "Administering discontinued prescriptions is not allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = MedicineAdministrationSerializer(
            data=request.data, context={"prescription": prescription_obj}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(prescription=prescription_obj, administered_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MedibaseViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)

    def serialize_data(self, objects: list[MedibaseMedicine]):
        return [medicine.get_representation() for medicine in objects]

    def list(self, request):
        try:
            limit = min(int(request.query_params.get("limit")), 30)
        except (ValueError, TypeError):
            limit = 30

        query = []
        if type := request.query_params.get("type"):
            query.append(MedibaseMedicine.type == type)

        if q := request.query_params.get("query"):
            query.append(
                (MedibaseMedicine.name == token_escaper.escape(q))
                | (MedibaseMedicine.vec % query_builder(q))
            )

        result = FindQuery(
            expressions=query, model=MedibaseMedicine, limit=limit
        ).execute(exhaust_results=False)

        return Response(self.serialize_data(result))
