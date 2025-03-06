# ruff : noqa : T201 F841

from django.core.management.base import BaseCommand

from care.emr.models import ValueSet
from care.emr.registries.care_valueset.care_valueset import SystemValueSet


class Command(BaseCommand):
    """ """

    help = "Sync Care ValueSets to Database. Optionally overwrite them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            default=False,
            type=bool,
            help="Overwrite the valueset if already present",
        )

    def handle(self, *args, **options):
        valuesets = SystemValueSet.get_all_valuesets()
        for valueset in valuesets:
            queryset = ValueSet.objects.filter(slug=valueset.slug)
            obj = queryset.first()
            if obj and not options["overwrite"]:
                continue
            if not obj:
                obj = ValueSet(slug=valueset.slug)
            obj.name = valueset.name
            obj.status = valueset.status
            obj.compose = valueset.composition.model_dump(exclude_defaults=True)
            obj.is_system_defined = True
            obj.save()
