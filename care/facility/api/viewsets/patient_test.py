from rest_framework import viewsets, status
from care.facility.models.patient_test import PatientTest, TestGroup, TestSession, TestValue
from care.facility.api.serializers.patient_test import TestGroupSerializer, PatientTestSerializer, TestValueSerializer
from rest_framework.permissions import IsAuthenticated
import uuid
from rest_framework import mixins
from rest_framework.response import Response
from django.db import transaction
from care.facility.models.patient_consultation import PatientConsultation
from django_filters import rest_framework as filters


class TestGroupFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class PatientTestFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")


class TestGroupViewset(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TestGroupSerializer
    queryset = TestGroup.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)
    filterset_class = TestGroupFilter


class PatientTestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PatientTestSerializer
    queryset = PatientTest.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)
    filterset_class = PatientTestFilter


class TestValueViewSet(viewsets.ModelViewSet):
    serializer_class = TestValueSerializer
    queryset = TestValue.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            consultation_id = PatientConsultation.objects.get(
                external_id=kwargs.get("consultation_external_id")
            ).id

            id = uuid.uuid4()
            session = TestSession(session=id)
            session.save()

            for value in request.data:
                value["session_id"] = session.id
                value["consultation"] = consultation_id

            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
