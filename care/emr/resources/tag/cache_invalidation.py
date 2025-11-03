from django.core.cache import cache

from care.emr.models.tag_config import TagConfig
from care.emr.resources.base import model_cache_key, model_string


def invalidate_tag_cache(tag_id, include_descendants=False):
    """
    Invalidate cache for a tag and optionally its descendants.

    Args:
        tag_id: ID of the tag to invalidate
        include_descendants: If True, also invalidates all descendant tags
    """
    if include_descendants:
        descendant_ids = list(
            TagConfig.objects.filter(parent_cache__overlap=[tag_id]).values_list(
                "id", flat=True
            )
        )
        all_tag_ids = [tag_id, *descendant_ids]
    else:
        all_tag_ids = [tag_id]

    TagConfig.objects.filter(id__in=all_tag_ids).update(cached_parent_json={})

    cache_keys = [
        model_cache_key(model_string(TagConfig), "TagConfigReadSpec", tid)
        for tid in all_tag_ids
    ]
    cache.delete_many(cache_keys)


def invalidate_tag_config_cache(sender, instance, **kwargs):
    """
    Invalidate cache for tag and related tags when a tag is updated.

    When a tag is saved:
    1. Invalidate the tag's own cache
    2. Invalidate all descendants' cache recursively (they store parent data)
    3. Invalidate parent's cache (has_children might have changed)
    """
    invalidate_tag_cache(instance.id, include_descendants=True)
    if instance.parent_id:
        invalidate_tag_cache(instance.parent_id, include_descendants=False)
