from celery.decorators import periodic_task
from celery.schedules import crontab
from django.db.models import Q, Subquery
from django.utils.timezone import now
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.models import Facility, FacilityRelatedSummary, PatientConsultation
from care.facility.summarisation.facility_capacity import FacilitySummaryFilter, FacilitySummarySerializer
from care.users.models import User


class PatientSummaryViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="PatientSummary").order_by("-created_date")
    permission_classes = (IsAuthenticated,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), facility__external_id=self.kwargs.get("external_id"))


def PatientSummary():
    facility_objects = Facility.objects.all()
    patient_summary = {}
    for facility_object in facility_objects:
        facility_id = facility_object.id
        if facility_id not in patient_summary:
            latest_patient_consultations = (
                PatientConsultation.objects.filter(facility=facility_id).distinct("patient").values("pk")
            )
            facility_patients = PatientConsultation.objects.filter(pk__in=Subquery(latest_patient_consultations))

            icu = Q(patient__is_active=True) & Q(admitted_to=2)
            ventilator = Q(patient__is_active=True) & Q(admitted_to=3)
            isolation = Q(patient__is_active=True) & Q(admitted_to=1)
            home_quarantine = Q(patient__is_active=True) & Q(suggestion="HI")

            total_patients_icu = facility_patients.filter(icu).count()
            total_patients_ventilator = facility_patients.filter(ventilator).count()
            total_patients_isolation = facility_patients.filter(isolation).count()
            total_patients_home_quarantine = facility_patients.filter(home_quarantine).count()

            facility_patients_today = facility_patients.filter(created_date__startswith=now().date())

            today_patients_icu = facility_patients_today.filter(icu).count()
            today_patients_isolation = facility_patients_today.filter(isolation).count()
            today_patients_ventilator = facility_patients_today.filter(ventilator).count()
            today_patients_home_quarantine = facility_patients_today.filter(home_quarantine).count()

            patient_summary[facility_id] = {
                "facility_name": facility_object.name,
                "district": facility_object.district.name,
                "total_patients_icu": total_patients_icu,
                "total_patients_ventilator": total_patients_ventilator,
                "total_patients_isolation": total_patients_isolation,
                "total_patients_home_quarantine": total_patients_home_quarantine,
                "today_patients_icu": today_patients_icu,
                "today_patients_ventilator": today_patients_ventilator,
                "today_patients_isolation": today_patients_isolation,
                "today_patients_home_quarantine": today_patients_home_quarantine,
            }

    for i in list(patient_summary.keys()):
        object_filter = Q(s_type="PatientSummary") & Q(created_date__startswith=now().date())
        if FacilityRelatedSummary.objects.filter(facility_id=i).filter(object_filter).exists():
            facility = FacilityRelatedSummary.objects.filter(object_filter).get(facility_id=i)
            facility.created_date = now()
            facility.data.pop("modified_date")
            if facility.data == patient_summary[i]:
                pass
            else:
                facility.data = patient_summary[i]
                latest_modification_date = now()
                facility.data.update({"modified_date": latest_modification_date.strftime("%d-%m-%Y %H:%M")})
                facility.save()
        else:
            modified_date = now()
            patient_summary[i].update({"modified_date": modified_date.strftime("%d-%m-%Y %H:%M")})
            FacilityRelatedSummary(s_type="PatientSummary", facility_id=i, data=patient_summary[i]).save()
    return True


@periodic_task(run_every=crontab(hour="*/1", minute=59))
def run_midnight():
    PatientSummary()
    print("Summarised Patients")
