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
        # /api/v1/patient/{patient_id}/post_covid
        with transaction.atomic():
            if kwargs.get("patient_external_id") is None:
                raise ValidationError({"error": "Patient id should be provided"})

            request.data["patient_id"] = PatientRegistration.objects.get(id=kwargs.get("patient_external_id"))

            data = {
                "symptoms": [9],
                "facility": "8298e97e-08f0-4d52-8838-0b1cd218dfe1",
                "patient": "f10b05c8-de76-4150-ae67-3392934faa45",
                "suggestion": "HI"  # confirm value
            }

            consultation = PatientConsultation(facility_id=1, patient_id=4)
            consultation.save()
            return super(PostCovidDataViewSet, self).create(request, *args, **kwargs)

    # def perform_create(self, serializer):
    #     print(self.kwargs)
    #     if self.kwargs.get("patient_external_id") is None:
    #         raise ValidationError({"error": "Patient id should be provided"})

    #     validated_data = serializer.validated_data
    #     # try:
    #     #     validated_data["patient"] = PatientRegistration.objects.get(
    #     #         id=self.kwargs.get("patient_external_id")
    #     #     )

    #     # except:
    #     #     raise ValidationError({"error": "Patient with patient id : " +
    #     #                           self.kwargs.get("patient_external_id") + "does not exist"})
    #     print(validated_data["treatment_facility"])
    #     with transaction.atomic():
    #         instance = serializer.create(validated_data)
    #     print(instance)
    #     return instance


# {
#     "symptoms": [2],
#     "facility": "8298e97e-08f0-4d52-8838-0b1cd218dfe1",
#     "patient": "f10b05c8-de76-4150-ae67-3392934faa45",
#     "suggestion": "HI"
# }

# {
#   "external_id": "1fa88f74-5716-4562-b3fc-2d963f66afb6",
#   "post_covid_time" : 1,
#   "date_of_onset_symptoms": "2021-04-16",
#   "date_of_test_positive": "2021-04-16",
#   "date_of_test_negative": "2021-04-16",
#   "testing_centre": "string",
#   "pre_covid_comorbidities": {},
#   "post_covid_comorbidities": {},
#   "treatment_duration": 0,
#   "covid_category": 1,
#   "vitals_at_admission": {
#         "pr" : 10,
#         "bp_systolic" : 10,
#         "bp_diastolic": 10,
#         "rr" : 10,
#         "spo2" : 10
#   },
#   "condition_on_admission": "string",
#   "condition_on_discharge": "string",
#   "icu_admission": true,
#   "oxygen_requirement": true,
#   "oxygen_requirement_detail": 1,
#   "mechanical_ventiltions_niv": 0,
#   "mechanical_ventiltions_invasive": 0,
#   "antivirals": true,
#   "antivirals_drugs": [
#     {"drug" : "some desc", "duration" : 2},
#     {"drug" : "some desc", "duration" : 2}
#   ],
#   "steroids": true,
#   "steroids_drugs": [
#     {"drug" : "some desc", "duration" : 2},
#     {"drug" : "some desc", "duration" : 2}
#   ],
#   "anticoagulants": true,
#   "anticoagulants_drugs": [
#     {"mode_of_transmission" : "IV", "drug" : "drug1", "duration" : 2}
#   ],
#   "antibiotics": true,
#   "antibiotics_drugs": [
#     {"drug" : "some desc", "duration" : 2},
#     {"drug" : "some desc", "duration" : 2}
#   ],
#   "antifungals": true,
#   "antifungals_drugs": [
#     {"drug" : "some desc", "duration" : 2},
#     {"drug" : "some desc", "duration" : 2}
#   ],
#   "documented_secondary_bacterial_infection": "string",
#   "documented_fungal_infection": "string",
#   "newly_detected_comorbidities": "string",
#   "worsening_of_comorbidities": "string",
#   "at_present_symptoms": [
#     "symptom1", "symptom2"
#   ],
#   "appearance_of_pallor": true,
#   "appearance_of_cyanosis": true,
#   "appearance_of_pedal_edema": true,
#   "appearance_of_pedal_edema_details": "string",
#   "systemic_examination": {
#       "respiratory" : {
#           "wob" : "some wob",
#           "rhonchi" : "some rhonchi",
#           "crepitation" : "some crepitation"
#       },
#       "cvs" : "some cvs",
#       "cns" : "some cns",
#       "git" : "some git"
#   },
#   "single_breath_count": "string",
#   "six_minute_walk_test": "string",
#   "concurrent_medications": "string",
#   "probable_diagnosis": "string",
#   "patient": 4,
#   "treatment_facility": [1]
# }
