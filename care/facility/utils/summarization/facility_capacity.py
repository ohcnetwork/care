from django.db.models import Sum
from django.utils.timezone import localtime, now

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import (
    Facility,
    FacilityCapacity,
    FacilityRelatedSummary,
    PatientRegistration,
)
from care.facility.models.inventory import (
    FacilityInventoryBurnRate,
    FacilityInventoryLog,
    FacilityInventorySummary,
)


def facility_capacity_summary():
    capacity_objects = FacilityCapacity.objects.all()
    capacity_summary = {}
    current_date = localtime(now()).replace(hour=0, minute=0, second=0, microsecond=0)

    for facility_obj in Facility.objects.all():
        # Calculate Actual Patients Discharged and Live in this Facility
        patients_in_facility = PatientRegistration.objects.filter(
            facility_id=facility_obj.id
        ).select_related("state", "district", "local_body")
        capacity_summary[facility_obj.id] = FacilitySerializer(facility_obj).data
        capacity_summary[facility_obj.id]["features"] = list(
            capacity_summary[facility_obj.id]["features"]
        )
        capacity_summary[facility_obj.id]["actual_live_patients"] = (
            patients_in_facility.filter(is_active=True).count()
        )
        discharge_patients = patients_in_facility.filter(is_active=False)
        capacity_summary[facility_obj.id]["actual_discharged_patients"] = (
            discharge_patients.count()
        )
        capacity_summary[facility_obj.id]["availability"] = []

        temp_inventory_summary_obj = {}
        summary_objs = FacilityInventorySummary.objects.filter(
            facility_id=facility_obj.id
        )
        for summary_obj in summary_objs:
            burn_rate = FacilityInventoryBurnRate.objects.filter(
                facility_id=facility_obj.id, item_id=summary_obj.item.id
            ).first()
            log_query = FacilityInventoryLog.objects.filter(
                facility_id=facility_obj.id,
                item_id=summary_obj.item.id,
                created_date__gte=current_date,
                probable_accident=False,
            )
            end_log = log_query.order_by("-created_date").first()
            end_stock = summary_obj.quantity
            if end_log:
                end_stock = end_log.current_stock
            total_consumed = 0
            temp1 = log_query.filter(is_incoming=False).aggregate(
                Sum("quantity_in_default_unit")
            )
            if temp1:
                total_consumed = temp1.get("quantity_in_default_unit__sum", 0) or 0
            total_added = 0
            temp2 = log_query.filter(is_incoming=True).aggregate(
                Sum("quantity_in_default_unit")
            )
            if temp2:
                total_added = temp2.get("quantity_in_default_unit__sum", 0) or 0

            start_stock = end_stock - total_added + total_consumed

            if burn_rate:
                burn_rate = burn_rate.burn_rate
            temp_inventory_summary_obj[summary_obj.item.id] = {
                "item_name": summary_obj.item.name,
                "stock": summary_obj.quantity,
                "unit": summary_obj.item.default_unit.name,
                "is_low": summary_obj.is_low,
                "burn_rate": burn_rate,
                "start_stock": start_stock,
                "end_stock": end_stock,
                "total_consumed": total_consumed,
                "total_added": total_added,
                "modified_date": summary_obj.modified_date.astimezone().isoformat(),
            }
        capacity_summary[facility_obj.id]["inventory"] = temp_inventory_summary_obj

    for capacity_object in capacity_objects:
        facility_id = capacity_object.facility_id
        if facility_id not in capacity_summary:
            # This facility is either deleted or not active
            continue
        if "availability" not in capacity_summary[facility_id]:
            capacity_summary[facility_id]["availability"] = []
        capacity_summary[facility_id]["availability"].append(
            FacilityCapacitySerializer(capacity_object).data
        )

    for i in capacity_summary:
        facility_summary_obj = None
        if FacilityRelatedSummary.objects.filter(
            s_type="FacilityCapacity",
            facility_id=i,
            created_date__gte=current_date,
        ).exists():
            facility_summary_obj = FacilityRelatedSummary.objects.get(
                s_type="FacilityCapacity",
                facility_id=i,
                created_date__gte=current_date,
            )
        else:
            facility_summary_obj = FacilityRelatedSummary(
                s_type="FacilityCapacity", facility_id=i
            )
        facility_summary_obj.data = capacity_summary[i]
        facility_summary_obj.save()

    return True
