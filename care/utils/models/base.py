from uuid import uuid4

from django.core.cache import cache
from django.db import models

from care.utils.registries.feature_flag import FlagName, FlagRegistry


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(deleted=False)


class BaseModel(models.Model):
    external_id = models.UUIDField(default=uuid4, unique=True, db_index=True)
    created_date = models.DateTimeField(
        auto_now_add=True, null=True, blank=True, db_index=True
    )
    modified_date = models.DateTimeField(
        auto_now=True, null=True, blank=True, db_index=True
    )
    deleted = models.BooleanField(default=False, db_index=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def delete(self, *args):
        self.deleted = True
        self.save(update_fields=["deleted"])


FLAGS_CACHE_TTL = 60 * 60 * 24  # 1 Day


class BaseFlag(BaseModel):
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
