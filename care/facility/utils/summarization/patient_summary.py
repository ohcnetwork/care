from django.db.models import Q
from django.utils.timezone import now

from care.facility.models import Facility, FacilityRelatedSummary, PatientRegistration
from care.facility.models.patient_base import BedTypeChoices


def patient_summary():
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

            for bed_type_choice in BedTypeChoices:
                db_value, text = bed_type_choice
                patient_filters = {
                    "last_consultation__" + "current_bed__bed__bed_type": db_value
                }
                count = patients.filter(**patient_filters).count()
                clean_name = "total_patients_" + "_".join(text.lower().split())
                patient_summary[facility_id][clean_name] = count

            home_quarantine = Q(last_consultation__suggestion="HI")

            total_patients_home_quarantine = patients.filter(home_quarantine).count()
            patient_summary[facility_id]["total_patients_home_quarantine"] = (
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
                patient_summary[facility_id][clean_name] = count

            # Update Anything Extra
            patient_summary[facility_id]["today_patients_home_quarantine"] = (
                today_patients_home_quarantine
            )

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
            if facility.data != patient_summary[i]:
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
