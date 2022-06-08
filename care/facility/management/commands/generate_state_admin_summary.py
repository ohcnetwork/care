from django.core.management.base import BaseCommand

from care.facility.reports.admin_reports import AdminReports, AdminReportsMode


class Command(BaseCommand):
    """
    Management command to Force start State Level Admin Reports.
    """

    help = "Generate State Level Admin Summary"

    def handle(self, *args, **options):
        print("Generating State Level Admin Reports")
        AdminReports(AdminReportsMode.STATE).generate_reports()
