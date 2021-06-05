from care.facility.models import patient
from celery.decorators import periodic_task
from celery.schedules import crontab
from django.db.models import Q, Subquery
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.cache import cache_page
from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.models import (
    PatientRegistration,
    Facility,
    FacilityRelatedSummary,
    PatientConsultation,
    ADMIT_CHOICES,
)
from care.facility.summarisation.facility_capacity import (
    FacilitySummaryFilter,
    FacilitySummarySerializer,
)


class PatientSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="PatientSummary").order_by(
        "-created_date"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    cache_limit = settings.API_CACHE_DURATION_IN_SECONDS

    @method_decorator(cache_page(cache_limit))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    # def get_queryset(self):
    #     user = self.request.user
    #     queryset = self.queryset
    #     if user.is_superuser:
    #         return queryset
    #     elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]:
    #         return queryset.filter(facility__district=user.district)
    #     elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]:
    #         return queryset.filter(facility__state=user.state)
    #     return queryset.filter(facility__users__id__exact=user.id)


def PatientSummary():
    facility_objects = Facility.objects.all()
    patient_summary = {}
    for facility_object in facility_objects:
        facility_id = facility_object.id
        if facility_id not in patient_summary:
            patient_summary[facility_id] = {
                "facility_name": facility_object.name,
                "district": facility_object.district.name,
                "facility_external_id": str(facility_object.external_id),
            }

            patients = PatientRegistration.objects.filter(
                is_active=True,
                last_consultation__discharge_date__isnull=True,
                last_consultation__facility=facility_object,
            )

            # Get Total Counts

            for admitted_choice in ADMIT_CHOICES:
                db_value = admitted_choice[0]
                text = admitted_choice[1]
                filter = {"last_consultation__" + "admitted_to": db_value}
                count = patients.filter(**filter).count()
                clean_name = "total_patients_" + "_".join(text.lower().split())
                patient_summary[facility_id][clean_name] = count

            home_quarantine = Q(last_consultation__suggestion="HI")

            total_patients_home_quarantine = patients.filter(home_quarantine).count()
            patient_summary[facility_id][
                "total_patients_home_quarantine"
            ] = total_patients_home_quarantine

            # Apply Date Filters

            patients_today = patients.filter(
                last_consultation__created_date__startswith=now().date()
            )

            # Get Todays Counts

            today_patients_home_quarantine = patients_today.filter(
                home_quarantine
            ).count()

            for admitted_choice in ADMIT_CHOICES:
                db_value = admitted_choice[0]
                text = admitted_choice[1]
                filter = {"last_consultation__" + "admitted_to": db_value}
                count = patients_today.filter(**filter).count()
                clean_name = "today_patients_" + "_".join(text.lower().split())
                patient_summary[facility_id][clean_name] = count

            # Update Anything Extra
            patient_summary[facility_id][
                "today_patients_home_quarantine"
            ] = today_patients_home_quarantine

    for i in list(patient_summary.keys()):
        object_filter = Q(s_type="PatientSummary") & Q(
            created_date__startswith=now().date()
        )
        if (
            FacilityRelatedSummary.objects.filter(facility_id=i)
            .filter(object_filter)
            .exists()
        ):
            facility = FacilityRelatedSummary.objects.filter(object_filter).get(
                facility_id=i
            )
            facility.created_date = now()
            facility.data.pop("modified_date")
            if facility.data == patient_summary[i]:
                pass
            else:
                facility.data = patient_summary[i]
                latest_modification_date = now()
                facility.data.update(
                    {
                        "modified_date": latest_modification_date.strftime(
                            "%d-%m-%Y %H:%M"
                        )
                    }
                )
                facility.save()
        else:
            modified_date = now()
            patient_summary[i].update(
                {"modified_date": modified_date.strftime("%d-%m-%Y %H:%M")}
            )
            FacilityRelatedSummary(
                s_type="PatientSummary", facility_id=i, data=patient_summary[i]
            ).save()
    return True


@periodic_task(run_every=crontab(hour="*/1", minute=59))
def run_midnight():
    PatientSummary()
    print("Summarised Patients")
