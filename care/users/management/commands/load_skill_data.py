from django.core.management import BaseCommand

from care.users.models import Skill


class Command(BaseCommand):
    """
    Command to load default skills
    """

    help = "Seed Data for Skills"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Skills Data... ", ending="")

        skills = [
            "Anesthesiologist",
            "Cardiac Surgeon",
            "Cardiologist",
            "Dentist",
            "Dermatologist",
            "Diabetologist",
            "Emergency Medicine Physician",
            "Endocrinologist",
            "Family Physician",
            "Gastroenterologist",
            "General Medicine",
            "General Surgeon",
            "Geriatrician",
            "Hematologist",
            "Immunologist",
            "Infectious Disease Specialist",
            "Intensivist",
            "MBBS doctor",
            "Medical Officer",
            "Nephrologist",
            "Neuro Surgeon",
            "Neurologist",
            "Obstetrician and Gynecologist",
            "Oncologist",
            "Oncology Surgeon",
            "Ophthalmologist",
            "Oral and Maxillofacial Surgeon",
            "Orthopedic",
            "Orthopedic Surgeon",
            "Otolaryngologist (ENT)",
            "Pediatrician",
            "Palliative care Physician",
            "Pathologist",
            "Pediatric Surgeon",
            "Physician",
            "Plastic Surgeon",
            "Psychiatrist",
            "Pulmonologist",
            "Radio technician",
            "Radiologist",
            "Rheumatologist",
            "Sports Medicine Specialist",
            "Thoraco-Vascular Surgeon",
            "Transfusion Medicine Specialist",
            "Urologist",
        ]

        Skill.objects.bulk_create(
            [Skill(name=skill) for skill in skills], ignore_conflicts=True
        )

        self.stdout.write(self.style.SUCCESS("OK"))
