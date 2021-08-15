from django.core.management.base import BaseCommand

from care.facility.reports.admin_reports import AdminReports, AdminReportsMode


class Command(BaseCommand):
    """
    Management command to Force start Admin Reports.
    """

    help = "Generate Admin Summary"

    def handle(self, *args, **options):
        print("Generating Admin Reports")
        AdminReports(AdminReportsMode.DISTRICT).generate_reports()
