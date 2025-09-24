import logging

from django.core.management.base import BaseCommand

from care.emr.models.encounter import Encounter
from care.emr.report_builder.html_constructor import HTMLConstructor, ReportBaseContext

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """ """

    help = ""

    def handle(self, *args, **options):
        data = {
            "name": "body",
            "type": "display",
            "properties": {"class": "main-container"},
            "children": [
                {
                    "name": "structured_list",
                    "type": "iteration",
                    "properties": {"class": "patient-data-list", "start": 1},
                    "children": [
                        {
                            "name": "encounter_data",
                            "type": "display",
                            "properties": {"datapoint": "encounter_class"},
                        },
                        {
                            "name": "constant",
                            "type": "display",
                            "properties": {"text": "Patient Data"},
                        },
                    ],
                }
            ],
        }

        html_constructor = HTMLConstructor.render_to_html(
            data,
            ReportBaseContext.encounter.value,
            Encounter.objects.order_by("-id").first(),
        )
        print(html_constructor)
