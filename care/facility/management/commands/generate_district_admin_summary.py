from django.core.management.base import BaseCommand

from care.facility.reports.admin_reports import AdminReports, AdminReportsMode


class Command(BaseCommand):
    """
    Management command to Force start District Level Admin Reports.
    """

    help = "Generate District Level Admin Summary"

    def handle(self, *args, **options):
        print("Generating District Level Admin Reports")
        AdminReports(AdminReportsMode.DISTRICT).generate_reports()
