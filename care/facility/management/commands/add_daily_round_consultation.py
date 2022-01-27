from django.core.management.base import BaseCommand

from care.facility.models import PatientConsultation, DailyRound


class Command(BaseCommand):
    """
    Management command to Populate daily round for consultations.
    """

    help = "Populate daily round for consultations"

    def handle(self, *args, **options):
        consultations = list(
            PatientConsultation.objects.filter(last_daily_round__isnull=True).values_list("external_id")
        )
        total_count = len(consultations)
        print(f"{total_count} Consultations need to be updated")
        i = 0
        for consultation_eid in consultations:
            if i > 10000 and i % 10000 == 0:
                print(f"{i} operations performed")
            i = i + 1
            PatientConsultation.objects.filter(external_id=consultation_eid[0]).update(
                last_daily_round=DailyRound.objects.filter(consultation__external_id=consultation_eid[0])
                .order_by("-created_date")
                .first()
            )
        print("Operation Completed")
