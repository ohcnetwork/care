from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.db.models import Q, Subquery
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.models import (
    ADMIT_CHOICES,
    DistrictScopedSummary,
    Facility,
    FacilityRelatedSummary,
    PatientConsultation,
    PatientRegistration,
    patient,
)

from care.users.models import District, LocalBody


class DistrictSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DistrictScopedSummary
        exclude = (
            "id",
            "s_type",
        )


class DistrictSummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="created_date", lookup_expr="lte")
    district = filters.NumberFilter(field_name="district__id")
    division = filters.NumberFilter(field_name="district__division__id")
    state = filters.NumberFilter(field_name="district__state__id")


class DistrictPatientSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = (
        DistrictScopedSummary.objects.filter(s_type="PatientSummary")
        .order_by("-created_date")
        .select_related("district", "district__state", "district__division")
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = DistrictSummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DistrictSummaryFilter

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


def DistrictPatientSummary():
    for district_object in District.objects.all():
        district_summary = {
            "name": district_object.name,
            "id": district_object.id,
        }
        for local_body_object in LocalBody.objects.filter(
            district_id=district_object.id
        ):
            district_summary[local_body_object.id] = {
                "name": local_body_object.name,
                "code": local_body_object.localbody_code,
                "total_inactive": PatientRegistration.objects.filter(
                    is_active=False, local_body_id=local_body_object.id,
                ).count(),
            }
            patients = PatientRegistration.objects.filter(
                is_active=True,
                last_consultation__discharge_date__isnull=True,
                local_body_id=local_body_object.id,
            )

            # Get Total Counts

            for admitted_choice in ADMIT_CHOICES:
                db_value = admitted_choice[0]
                text = admitted_choice[1]
                filter = {"last_consultation__" + "admitted_to": db_value}
                count = patients.filter(**filter).count()
                clean_name = "total_patients_" + "_".join(text.lower().split())
                district_summary[local_body_object.id][clean_name] = count

            home_quarantine = Q(last_consultation__suggestion="HI")

            total_patients_home_quarantine = patients.filter(home_quarantine).count()
            district_summary[local_body_object.id][
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
                district_summary[local_body_object.id][clean_name] = count

            # Update Anything Extra
            district_summary[local_body_object.id][
                "today_patients_home_quarantine"
            ] = today_patients_home_quarantine

        object_filter = Q(s_type="PatientSummary") & Q(
            created_date__startswith=now().date()
        )
        if (
            DistrictScopedSummary.objects.filter(district_id=district_object.id)
            .filter(object_filter)
            .exists()
        ):
            district_summary_old = DistrictScopedSummary.objects.filter(
                object_filter
            ).get(district_id=district_object.id)
            district_summary_old.created_date = now()
            district_summary_old.data.pop("modified_date")

            district_summary_old.data = district_summary
            latest_modification_date = now()
            district_summary_old.data.update(
                {"modified_date": latest_modification_date.strftime("%d-%m-%Y %H:%M")}
            )
            district_summary_old.save()
        else:
            modified_date = now()
            district_summary.update(
                {"modified_date": modified_date.strftime("%d-%m-%Y %H:%M")}
            )
            DistrictScopedSummary(
                s_type="PatientSummary",
                district_id=district_object.id,
                data=district_summary,
            ).save()
    return True


@periodic_task(run_every=crontab(hour="*/1", minute=59))
def run_midnight():
    DistrictPatientSummary()
    print("Summarised Patients")
