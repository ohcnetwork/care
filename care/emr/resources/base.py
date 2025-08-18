import datetime
from typing import Annotated, Any, Union

import phonenumbers
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_save
from django.utils.timezone import is_naive
from pydantic import BaseModel, model_validator
from pydantic_extra_types.phone_numbers import PhoneNumberValidator


class EMRResource(BaseModel):
    __model__ = None
    __exclude__ = []
    meta: dict = {}
    __questionnaire_cache__ = {}
    __store_metadata__ = False

    @classmethod
    def get_database_mapping(cls):
        """
        Mapping of database fields to pydantic object
        """
        database_fields = []
        for field in cls.__model__._meta.fields:  # noqa SLF001
            # Exclude foreign key fields
            if not isinstance(field, models.ForeignKey):
                database_fields.append(field.name)
        return database_fields

    @classmethod
    def get_serializer_context(cls, info):
        if info and info.context:
            return info.context
        return {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj, *args, **kwargs):
        mapping["id"] = obj.external_id

    @classmethod
    def perform_extra_user_serialization(cls, mapping, obj, user, *args, **kwargs):
        pass

    def is_update(self):
        return getattr("_is_update", False)

    @classmethod
    def serialize(cls, obj: __model__, user=None, *args, **kwargs):
        """
        Creates a pydantic object from a database object
        """
        mappings = cls.get_database_mapping()
        constructed = {}
        for mapping in mappings:
            if mapping in cls.model_fields and mapping not in cls.__exclude__:
                constructed[mapping] = getattr(obj, mapping)
        if cls.__store_metadata__:
            for field in getattr(obj, "meta", {}):
                if field in cls.model_fields:
                    constructed[field] = obj.meta[field]
        cls.perform_extra_serialization(constructed, obj, *args, **kwargs)
        if user:
            cls.perform_extra_user_serialization(
                constructed,
                obj,
                *args,
                **kwargs,
                user=user,
            )
        return cls.model_construct(**constructed)

    def perform_extra_deserialization(self, is_update, obj):
        pass

    def de_serialize(self, obj=None, partial=False):
        """
        Creates a database object from a pydantic object
        """
        is_update = True
        if not obj:
            is_update = False
            obj = self.__model__()
        database_fields = self.get_database_mapping()
        meta = getattr(obj, "meta", {})
        dump = self.model_dump(mode="json", exclude_defaults=True)
        for field in dump:
            if (
                field in database_fields
                and field not in self.__exclude__
                and field not in ["id", "external_id"]
            ):
                obj.__setattr__(field, dump[field])
            elif field not in self.__exclude__ and self.__store_metadata__:
                meta[field] = dump[field]
        obj.meta = meta

        self.perform_extra_deserialization(is_update, obj)
        return obj

    # @classmethod
    # def as_questionnaire(cls, parent_classes=None):
    #     """
    #     This is created so that the FE has an idea about bound valuesets and other metadata about the form
    #     Maybe we can speed up this process by starting with model's JSON Schema
    #     Pydantic provides that by default for all models
    #     """
    #     if not parent_classes:
    #         parent_classes = []
    #     if cls.__questionnaire_cache__:
    #         return cls.__questionnaire_cache__
    #     questionnire_obj = []
    #     for field in cls.model_fields:
    #         field_class = cls.model_fields[field]
    #         field_obj = {"linkId": field}
    #         field_type = field_class.annotation
    #
    #         if type(field_type) is UnionType:
    #             field_type = field_type.__args__[0]
    #
    #         if get_origin(field_type) is list:
    #             field_obj["repeats"] = True
    #             field_type = field_type.__args__[0]
    #
    #         if field_type in parent_classes:
    #             # Avoiding circular references
    #             continue
    #
    #         if issubclass(field_type, Enum):
    #             field_obj["type"] = "string"
    #             field_obj["answer_options"] = [{x.name: x.value} for x in field_type]
    #         elif issubclass(field_type, datetime.datetime):
    #             field_obj["type"] = "dateTime"
    #         elif issubclass(field_type, str):
    #             field_obj["type"] = "string"
    #         elif issubclass(field_type, int):
    #             field_obj["type"] = "integer"
    #         elif issubclass(field_type, uuid.UUID):
    #             field_obj["type"] = "string"
    #         elif field_type is Coding:
    #             field_obj["type"] = "coding"
    #             field_obj["valueset"] = {"slug": field_class.json_schema_extra["slug"]}
    #         elif issubclass(field_type, EMRResource):
    #             field_obj["type"] = "group"
    #             parent_classes = parent_classes[::]
    #             parent_classes.append(cls)
    #             field_obj["questions"] = field_type.as_questionnaire(parent_classes)
    #         questionnire_obj.append(field_obj)
    #     cls.__questionnaire_cache__ = questionnire_obj
    #     return questionnire_obj

    def to_json(self):
        return self.model_dump(mode="json", exclude=["meta"])

    @classmethod
    def serialize_audit_users(cls, mapping, obj):
        from care.emr.resources.user.spec import UserSpec

        if obj.created_by_id:
            mapping["created_by"] = model_from_cache(UserSpec, id=obj.created_by_id)
        if obj.updated_by_id:
            mapping["updated_by"] = model_from_cache(UserSpec, id=obj.updated_by_id)


PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber()],  # noqa: UP007
    PhoneNumberValidator(
        default_region=None,
        supported_regions=[],
        number_format="E164",
    ),
]


class PeriodSpec(BaseModel):
    start: datetime.datetime | None = None
    end: datetime.datetime | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.start and is_naive(self.start):
            raise ValueError("Start Date must be timezone aware")
        if self.end and is_naive(self.end):
            raise ValueError("End Date must be timezone aware")
        if (self.start and self.end) and (self.start > self.end):
            raise ValueError("Start Date cannot be greater than End Date")
        return self


def model_string(model: models.Model) -> str:
    """
    Returns a string representation of the model class.

    e.g. "app_label.ModelName"
    """
    return f"{model._meta.app_label}.{model.__name__}"  # noqa: SLF001


def model_cache_key(
    db_model_name, model_name: str | None = None, pk: int | None = None
) -> str:
    """Generate a cache key for model data.

    This function creates a standardized cache key format using database model name,
    model name and pk. The format is "db_model_name:pk:model_name" where pk and
    model_name are replaced with '*' if not provided.

    Args:
        db_model_name: Name of the database model in format "app_label.ModelName".
        model_name (str | None): Optional name of the model. Defaults to None.
        pk (int | None): Optional model ID. Defaults to None.

    Returns:
        str: Formatted cache key string in the format "db_model_name:id:model_name"

    Examples:
        >>> model_cache_key("emr.Patient", "BasicInfo", 123)
        'serializers_cache:emr.Patient:123:BasicInfo'
        >>> model_cache_key("emr.Doctor")
        'serializers_cache:emr.Doctor:*:*'
    """

    return f"serializers_cache:{db_model_name}:{pk or '*'}:{model_name or '*'}"


def model_from_cache(model: EMRResource, quiet=True, **kwargs) -> dict[str, Any] | None:
    """
    Fetch a cacheable model instance from the cache or database.
    """
    if not isinstance(model, type):
        raise TypeError("model must be a class not an instance")
    if not getattr(model, "__cacheable__", False):
        raise ValueError(
            "Model is not cacheable. Use @cacheable decorator to mark it as cacheable."
        )

    db_model: models.Model = model.__model__
    if db_model is None:
        raise ValueError("Model must have a __model__ attribute")

    pk: int | str | None = (
        kwargs.get("pk") or kwargs.get("id") or kwargs.get("external_id")
    )
    if not pk:
        raise ValueError(
            "kwargs must contain a unique identifier (pk, id, or external_id)"
        )

    data: dict[str, Any] | None = cache.get(
        model_cache_key(model_string(db_model), model.__name__, pk)
    )

    if not data:
        db_model_manager = db_model.objects
        if getattr(model, "__cacheable_use_base_manager__", False):
            # bypass the custom manager to allow fetching deleted objects
            db_model_manager = db_model._base_manager  # noqa: SLF001

        obj = db_model_manager.filter(**kwargs).first()
        if not obj:
            if not quiet:
                msg = f"Model {model.__name__} with {kwargs} not found in database."
                raise ValueError(msg)
            return None

        data = model.serialize(obj)
        cache.set(model_cache_key(model_string(db_model), model.__name__, pk), data)

    return dict(data)


# TODO: add param for manually adding dependencies for cache invalidation
def cacheable(_model: EMRResource = None, use_base_manager=False) -> EMRResource:
    """
    Decorator to mark a model as cacheable.
    This will set up the necessary signals to clear the cache
    when the model is saved or deleted, and will also set the __cacheable__ attribute
    to True on the model class
    """

    def decorator(model: EMRResource, use_base_manager) -> EMRResource:
        if not hasattr(model, "__model__"):
            raise ValueError("Model must have a __model__ attribute")

        db_model: models.Model = model.__model__

        post_save.connect(
            delete_model_cache,
            sender=db_model,
            dispatch_uid=f"delete_model_cache:{model_string(db_model)}",
        )

        model.__cacheable__ = True
        model.__cacheable_use_base_manager__ = use_base_manager
        return model

    if _model is None:
        return lambda model: decorator(model, use_base_manager)
    return decorator(_model, use_base_manager)


def delete_model_cache(sender, instance, **kwargs) -> None:
    """
    Signal handler to delete the cache for a model instance when it is saved or deleted.
    """
    sender_model_string = model_string(sender)
    cache.delete(model_cache_key(sender_model_string, pk=instance.id))
