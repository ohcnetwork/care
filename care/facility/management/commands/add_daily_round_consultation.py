from django.core.management.base import BaseCommand

from care.facility.models import PatientConsultation, DailyRound


class Command(BaseCommand):
    """
    Management command to Populate daily round for consultations.
    """

    help = "Populate daily round for consultations"

    def handle(self, *args, **options):
        consultations = list(PatientConsultation.objects.filter(last_daily_round__isnull=True).values_list("id"))
        total_count = len(consultations)
        print(f"{total_count} Consultations need to be updated")
        i = 0
        for consultation_id in consultations:
            if i > 10000 and i % 10000 == 0:
                print(f"{i} operations performed")
            i = i + 1
            PatientConsultation.objects.filter(id=consultation_id).update(
                last_daily_round=DailyRound.objects.filter(consultation_id=consultation_id)
                .order_by("-created_date")
                .first()
            )
        print("Operation Completed")
