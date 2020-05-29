from django_filters import rest_framework as filters

from apps.accounts import models as accounts_models
from apps.facility import models as facility_models


class FacilityFilter(filters.FilterSet):
    code = filters.CharFilter(field_name="facility_code", lookup_expr="istartswith")
    name = filters.CharFilter(field_name="name", lookup_expr="istartswith")
    address = filters.CharFilter(field_name="address", lookup_expr="istartswith")
    facility_type_name = filters.CharFilter(
        field_name="facility_type__name", lookup_expr="istartswith"
    )
    owned_by_name = filters.CharFilter(
        field_name="owned_by__name", lookup_expr="istartswith"
    )
    total_patient = filters.RangeFilter(field_name="total_patient", lookup_expr="range")
    positive_patient = filters.RangeFilter(
        field_name="positive_patient", lookup_expr="range"
    )
    negative_patient = filters.RangeFilter(
        field_name="negative_patient", lookup_expr="range"
    )
    created_at = filters.DateTimeFromToRangeFilter(field_name="created_at")
    updated_at = filters.DateTimeFromToRangeFilter(field_name="updated_at")
    district = filters.filters.ModelMultipleChoiceFilter(
        field_name='district',
        queryset=accounts_models.District.objects.all()
    )

    class Meta:
        model = facility_models.Facility
        fields = (
            "name",
            "code",
            "address",
            "district",
            "facility_type_name",
            "owned_by_name",
            "district",
            "total_patient",
            "positive_patient",
            "negative_patient",
            "created_at",
            "updated_at",
        )


class InventoryFilter(filters.FilterSet):
    inventory_type = filters.CharFilter(field_name="item__name")
    facility_name = filters.CharFilter(
        field_name="facility__name", lookup_expr="istartswith"
    )
    required_quantity = filters.RangeFilter(
        field_name="required_quantity", lookup_expr="range"
    )
    current_quantity = filters.RangeFilter(
        field_name="current_quantity", lookup_expr="range"
    )

    class Meta:
        model = facility_models.Inventory
        fields = (
            "inventory_type",
            "facility_name",
            "required_quantity",
            "current_quantity",
        )
