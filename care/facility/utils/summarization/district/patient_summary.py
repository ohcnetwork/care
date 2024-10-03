from django.db.models import Q
from django.utils.timezone import now

from care.facility.models import DistrictScopedSummary, PatientRegistration
from care.facility.models.patient_base import BedTypeChoices
from care.users.models import District, LocalBody


def district_patient_summary():
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
                    is_active=False,
                    local_body_id=local_body_object.id,
                ).count(),
            }
            patients = PatientRegistration.objects.filter(
                is_active=True,
                last_consultation__discharge_date__isnull=True,
                local_body_id=local_body_object.id,
            )

            # Get Total Counts

            for bed_type_choice in BedTypeChoices:
                db_value, text = bed_type_choice
                patient_filters = {
                    "last_consultation__" + "current_bed__bed__bed_type": db_value
                }
                count = patients.filter(**patient_filters).count()
                clean_name = "total_patients_" + "_".join(text.lower().split())
                district_summary[local_body_object.id][clean_name] = count

            home_quarantine = Q(last_consultation__suggestion="HI")

            total_patients_home_quarantine = patients.filter(home_quarantine).count()
            district_summary[local_body_object.id]["total_patients_home_quarantine"] = (
                total_patients_home_quarantine
            )

            # Apply Date Filters

            patients_today = patients.filter(
                last_consultation__created_date__startswith=now().date()
            )

            # Get Todays Counts

            today_patients_home_quarantine = patients_today.filter(
                home_quarantine
            ).count()

            for bed_type_choice in BedTypeChoices:
                db_value, text = bed_type_choice
                patient_filters = {
                    "last_consultation__" + "current_bed__bed__bed_type": db_value
                }
                count = patients_today.filter(**patient_filters).count()
                clean_name = "today_patients_" + "_".join(text.lower().split())
                district_summary[local_body_object.id][clean_name] = count

            # Update Anything Extra
            district_summary[local_body_object.id]["today_patients_home_quarantine"] = (
                today_patients_home_quarantine
            )

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
            district_summary["modified_date"] = modified_date.strftime("%d-%m-%Y %H:%M")
            DistrictScopedSummary(
                s_type="PatientSummary",
                district_id=district_object.id,
                data=district_summary,
            ).save()
    return True
