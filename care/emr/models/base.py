from django.core.cache import cache
from django.db import models

from care.utils.models.base import BaseModel
from care.utils.registries.feature_flag import FlagName, FlagRegistry


class EMRBaseModel(BaseModel):
    history = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_updated_by",
    )

    class Meta:
        abstract = True


FLAGS_CACHE_TTL = 60 * 60 * 24  # 1 Day


class BaseFlag(EMRBaseModel):
    flag = models.CharField(max_length=1024)

    cache_key_template = ""
    all_flags_cache_key_template = ""
    flag_type = None
    entity_field_name = ""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.validate_flag(self.flag)
        cache.delete(
            self.cache_key_template.format(
                entity_id=self.entity_id, flag_name=self.flag
            )
        )
        cache.delete(self.all_flags_cache_key_template.format(entity_id=self.entity_id))
        return super().save(*args, **kwargs)

    @property
    def entity(self):
        return getattr(self, self.entity_field_name)

    @property
    def entity_id(self):
        return getattr(self, f"{self.entity_field_name}_id")

    @classmethod
    def validate_flag(cls, flag_name: FlagName):
        FlagRegistry.validate_flag_name(cls.flag_type, flag_name)

    @classmethod
    def check_entity_has_flag(cls, entity_id: int, flag_name: FlagName) -> bool:
        cls.validate_flag(flag_name)
        return cache.get_or_set(
            cls.cache_key_template.format(entity_id=entity_id, flag_name=flag_name),
            default=lambda: cls.objects.filter(
                **{f"{cls.entity_field_name}_id": entity_id, "flag": flag_name}
            ).exists(),
            timeout=FLAGS_CACHE_TTL,
        )

    @classmethod
    def get_all_flags(cls, entity_id: int) -> tuple[FlagName]:
        return cache.get_or_set(
            cls.all_flags_cache_key_template.format(entity_id=entity_id),
            default=lambda: tuple(
                cls.objects.filter(
                    **{f"{cls.entity_field_name}_id": entity_id}
                ).values_list("flag", flat=True)
            ),
            timeout=FLAGS_CACHE_TTL,
        )

    @classmethod
    def invalidate_cache(cls, entity_id: int, flag_name: str):
        cache.delete(
            cls.cache_key_template.format(entity_id=entity_id, flag_name=flag_name)
        )
        cache.delete(cls.all_flags_cache_key_template.format(entity_id=entity_id))
