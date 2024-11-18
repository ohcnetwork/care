from django.conf import settings
from django.db import models
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from rest_framework.exceptions import ValidationError


class CSVExportViewSetMixin:
    """Mixin that adds CSV export functionality to a viewset"""

    csv_export_limit = 7
    date_range_fields = []

    def get_model(self):
        """Get model class from viewset's queryset or model attribute"""
        if hasattr(self, "queryset"):
            return self.queryset.model
        if hasattr(self, "model"):
            return self.model
        msg = (
            "Cannot determine model class from viewset, set model or queryset attribute"
        )
        raise ValueError(msg)

    def get_date_range_fields(self):
        """Get date range fields from model and filterset"""
        if self.date_range_fields:
            return self.date_range_fields

        model = self.get_model()
        date_fields = []

        # Get fields from model that are DateField/DateTimeField
        for field in model._meta.fields:  # noqa: SLF001
            if isinstance(field, (models.DateField, models.DateTimeField)):
                date_fields.append(field.name)

        # Get date range fields from filterset if defined
        if hasattr(self, "filterset_class"):
            for name, field in self.filterset_class.declared_filters.items():
                if isinstance(field, filters.DateFromToRangeFilter):
                    date_fields.append(name)

        return list(set(date_fields))

    def get_csv_settings(self):
        """Get CSV export configuration from model"""
        model = self.get_model()

        # Try to get settings from model
        annotations = getattr(model, "CSV_ANNOTATE_FIELDS", {})
        field_mapping = getattr(model, "CSV_MAPPING", {})
        field_serializers = getattr(model, "CSV_MAKE_PRETTY", {})

        if not field_mapping:
            # Auto-generate field mapping from model fields
            field_mapping = {f.name: f.verbose_name.title() for f in model._meta.fields}  # noqa: SLF001

        fields = list(field_mapping.keys())

        return {
            "annotations": annotations,
            "field_mapping": field_mapping,
            "field_serializers": field_serializers,
            "fields": fields,
        }

    def validate_date_ranges(self, request):
        """Validates that at least one date range filter is within limits"""
        filterset = filters.DjangoFilterBackend().get_filterset(
            request, self.queryset, self
        )
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

        within_limits = False
        for field in self.get_date_range_fields():
            slice_obj = filterset.form.cleaned_data.get(field)
            if slice_obj:
                if not slice_obj.start or not slice_obj.stop:
                    raise ValidationError(
                        {
                            field: "both starting and ending date must be provided for export"
                        }
                    )

                days_difference = (
                    filterset.form.cleaned_data.get(field).stop
                    - filterset.form.cleaned_data.get(field).start
                ).days

                if days_difference <= self.csv_export_limit:
                    within_limits = True
                else:
                    raise ValidationError(
                        {
                            field: f"Cannot export more than {self.csv_export_limit} days at a time"
                        }
                    )

        if not within_limits:
            raise ValidationError(
                {
                    "date": f"At least one date field must be filtered to be within {self.csv_export_limit} days"
                }
            )

    def export_as_csv(self, request):
        """Exports queryset as CSV"""
        self.validate_date_ranges(request)

        csv_settings = self.get_csv_settings()
        queryset = self.filter_queryset(self.get_queryset())

        if csv_settings["annotations"]:
            queryset = queryset.annotate(**csv_settings["annotations"])

        queryset = queryset.values(*csv_settings["fields"])

        return render_to_csv_response(
            queryset,
            field_header_map=csv_settings["field_mapping"],
            field_serializer_map=csv_settings["field_serializers"],
        )

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            return self.export_as_csv(request)
        return super().list(request, *args, **kwargs)
