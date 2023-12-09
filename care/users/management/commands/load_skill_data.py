from django.core.management import BaseCommand

from care.users.models import Skill


class Command(BaseCommand):
    """
    Command to load default skills
    """

    help = "Seed Data for Skills"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Skills Data... ", ending="")

        skills = [
            "Anesthesiologist",
            "Cardiac Surgeon",
            "Cardiologist",
            "Dermatologist",
            "Diabetologist",
            "Emergency Medicine Physician",
            "Endocrinologist",
            "Family Physician",
            "Gastroenterologist",
            "General Medicine",
            "General Surgeon",
            "Hematologist",
            "Intensivist",
            "Medical Officer",
            "Nephrologist",
            "Neuro Surgeon",
            "Neurologist",
            "Obstetrician and Gynecologist",
            "Oncologist",
            "Oncology Surgeon",
            "Ophthalmologist",
            "Orthopedic",
            "Orthopedic Surgeon",
            "Otolaryngologist (ENT)",
            "Pediatrician",
            "Palliative care Physician",
            "Pathologist",
            "Physician",
            "Plastic Surgeon",
            "Psychiatrist",
            "Pulmonologist",
            "Radio technician",
            "Radiologist",
            "Rheumatologist",
            "Thoraco-Vascular Surgeon",
            "Urologist",
        ]

        Skill.objects.bulk_create(
            [Skill(name=skill) for skill in skills], ignore_conflicts=True
        )

        self.stdout.write(self.style.SUCCESS("OK"))
