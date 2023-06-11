from typing import Optional, Type

from django.core.paginator import Paginator
from django.db.models import Count, Model, Q


def update_related_counts(
    model: Type[Model],
    related_counts: dict[str, tuple[str, Q]],
    filters: Optional[Q] = None,
    sort_by: Optional[str] = "id",
) -> None:
    """
    Updates the related counts for a queryset of objects using pagination and bulk update.

    Args:
        model: The model for which the related counts need to be updated.
        related_counts: A dictionary containing the field names as keys and a tuple of
            related_name and related_filter as values.
        sort_by: The field used to order the queryset. Defaults to "id".
        filters: An optional filter to apply on the queryset. Defaults to None.

    Example:
        update_related_counts(Facility, {
            "patient_count": (
                "patientregistration",
                Q(patientregistration__is_active=True, patientregistration__deleted=False),
            ),
            "bed_count": ("bed", Q(bed__is_active=True, bed__deleted=False)),
            filters=Q(deleted=False),
        })
    """
    queryset = model.objects.order_by(sort_by)
    if filters:
        queryset = queryset.filter(filters)

    paginator = Paginator(queryset, 1000)

    for page_number in range(1, paginator.num_pages + 1):
        page = paginator.page(page_number)

        annotations = {
            f"annotated_{field_name}": Count(related_name, filter=related_filter)
            for field_name, (related_name, related_filter) in related_counts.items()
        }
        queryset = page.object_list.annotate(**annotations)

        updated_objects = []
        for obj in queryset:
            for field_name in related_counts:
                setattr(obj, field_name, getattr(obj, f"annotated_{field_name}"))
            updated_objects.append(obj)

        model.objects.bulk_update(
            updated_objects, list(related_counts.keys()), batch_size=1000
        )


def update_related_count_for_single_object(
    obj: Model, related_counts: dict[str, tuple[str, Q]]
) -> None:
    """
    Updates the related counts for a single object.

    Args:
        obj: The object for which the related counts need to be updated.
        related_counts: A dictionary containing the field names as keys and a tuple of
            related_model_manager and related_filter as values.

    Example:
        update_related_count_for_single_object(facility, {
            "patient_count": (
                "patientregistration_set",
                Q(is_active=True, deleted=False),
            ),
            "bed_count": ("bed_set", Q(is_active=True, deleted=False)),
        })
    """
    for field_name, (related_model_manager, related_filter) in related_counts.items():
        count = getattr(obj, related_model_manager).filter(related_filter).count()
        setattr(obj, field_name, count)
    obj.save()
