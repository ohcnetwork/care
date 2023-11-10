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
            "Anesthetists",
            "Cardiac Surgeon",
            "Cardiologist",
            "Dermatologist",
            "Diabetologist",
            "Emergency Medicine Physcian",
            "Endocrinologist",
            "Family Physcian",
            "Gastroenterologist",
            "General Medicine",
            "General Surgeon",
            "Hematologist",
            "Intensivists",
            "Medical Officer",
            "Nephrologist",
            "Neuro Surgeon",
            "Neurologist",
            "obstetrician and Gynecologists",
            "Oncologist",
            "Oncology Surgeon",
            "Opthalmologists",
            "orthopaedic Surgeon",
            "Orthopaedician",
            "Otolaryngologist ( ENT )",
            "Palliative care Physcian",
            "Pathologists",
            "Pediatrician",
            "Physcian",
            "Plastic Surgeon",
            "Psychiatrists",
            "Pulmonologists",
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
