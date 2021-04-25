from rest_framework import viewsets, status
from care.facility.models.post_covid_data import PostCovidData
from care.facility.api.serializers.post_covid_data import PostCovidDataSerializer
from rest_framework.permissions import IsAuthenticated
from care.facility.models import User
from rest_framework.response import Response
from django.db import transaction
from rest_framework.exceptions import ValidationError
from care.facility.models.patient import PatientRegistration
from care.facility.api.serializers.patient_consultation import PatientConsultationSerializer
from care.facility.models.patient_consultation import PatientConsultation
from care.facility.models.facility import Facility


class PostCovidDataViewSet(viewsets.ModelViewSet):
    serializer_class = PostCovidDataSerializer
    queryset = PostCovidData.objects.all()
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(patient__facility__state=self.request.user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__facility__district=self.request.user.district)
        filters = Q(patient__facility__users__id__exact=self.request.user.id)
        filters |= Q(assigned_to=self.request.user)
        return self.queryset.filter(filters).distinct("id")

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            if kwargs.get("patient_external_id") is None:
                raise ValidationError({"error": "Patient id should be provided"})

            request.data["patient_id"] = PatientRegistration.objects.get(
                external_id=kwargs.get("patient_external_id")).id
            patient = PatientRegistration.objects.get(id=request.data["patient_id"])

            consultation = PatientConsultation(facility_id=patient.facility.id, patient_id=patient.id)
            consultation.save()

            request.data["consultation"] = consultation.id

            facilities = []
            for id in request.data["treatment_facility"]:
                facilities.append(Facility.objects.get(external_id=id).id)

            request.data["treatment_facility"] = facilities
            print("heyyyy ending create")
            print(request.data)
            return super(PostCovidDataViewSet, self).create(request, *args, **kwargs)
