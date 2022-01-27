from django.core.management.base import BaseCommand

from care.facility.models import PatientConsultation, DailyRound


class Command(BaseCommand):
    """
    Management command to Populate daily round for consultations.
    """

    help = "Populate daily round for consultations"

    def handle(self, *args, **options):
        consultations = PatientConsultation.objects.filter(last_daily_round__isnull=True)
        total_count = consultations.count()
        print(f"{total_count} Consultations need to be updated")
        i = 0
        for consultation in consultations:
            if i > 10000 and i % 10000 == 0:
                print(f"{i} operations performed")
            i = i + 1
            PatientConsultation.objects.filter(id=consultation.id).update(
                last_daily_round=DailyRound.objects.filter(consultation_id=consultation.id)
                .order_by("-created_date")
                .first()
            )
        print("Operation Completed")
