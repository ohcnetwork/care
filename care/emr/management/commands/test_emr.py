# ruff : noqa : T201 F841

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """ """

    help = ""

    def handle(self, *args, **options):
        from django.db import transaction

        from care.emr.models import Organization, Patient
        from care.facility.models import Facility

        with transaction.atomic():
            districts = Organization.objects.filter(level_cache=1)
            for district in districts:
                # Generate New District Panchayat
                district_panchayat_name = district.name + " District Panchayat"
                district_panchayat_org, _ = Organization.objects.get_or_create(
                    org_type="govt",
                    system_generated=True,
                    name=district_panchayat_name,
                    parent=district,
                )
                # Connect District Panchayat to the District as child
                district_panchayat_org.metadata = {
                    "country": "India",
                    "govt_org_type": "district_panchayat",
                    "govt_org_children_type": "block_panchayat",
                }
                district_panchayat_org.save()
                block_panchayats = Organization.objects.filter(
                    parent=district, metadata__govt_org_type="block_panchayat"
                )
                # Connect all the block panchayats under the District Panchayat
                for i in block_panchayats:
                    i.parent = district_panchayat_org
                    i.save()
            # Reset all cache
            qs = Organization.objects.filter(org_type="govt")
            qs.update(level_cache=0)
            # Generate cache again
        for i in range(7):
            print("Getting There, Iteration", i)
            for obj in Organization.objects.filter(org_type="govt"):
                obj.set_organization_cache()
        qs.update(cached_parent_json={})
        facilities = Facility.objects.all()
        for facility in facilities:
            facility.sync_cache()
        patients = Patient.objects.all()
        for patient in patients:
            patient.save()
