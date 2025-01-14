import datetime
import uuid
from enum import Enum
from types import UnionType
from typing import Annotated, Union, get_origin

import phonenumbers
from pydantic import BaseModel
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from care.emr.fhir.schema.base import Coding


class EMRResource(BaseModel):
    __model__ = None
    __exclude__ = []
    meta: dict = {}
    __questionnaire_cache__ = {}

    @classmethod
    def get_database_mapping(cls):
        """
        Mapping of database fields to pydantic object
        """
        database_fields = []
        for field in cls.__model__._meta.fields:  # noqa SLF001
            database_fields.append(field.name)
        return database_fields

    @classmethod
    def get_serializer_context(cls, info):
        if info and info.context:
            return info.context
        return {}

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

    @classmethod
    def perform_extra_user_serialization(cls, mapping, obj, user):
        pass

    def is_update(self):
        return getattr("_is_update", False)

    @classmethod
    def serialize(cls, obj: __model__, user=None):
        """
        Creates a pydantic object from a database object
        """
        mappings = cls.get_database_mapping()
        constructed = {}
        for mapping in mappings:
            if mapping in cls.model_fields and mapping not in cls.__exclude__:
                constructed[mapping] = getattr(obj, mapping)
        for field in getattr(obj, "meta", {}):
            if field in cls.model_fields:
                constructed[field] = obj.meta[field]
        cls.perform_extra_serialization(constructed, obj)
        if user:
            cls.perform_extra_user_serialization(constructed, obj, user=user)
        return cls.model_construct(**constructed)

    def perform_extra_deserialization(self, is_update, obj):
        pass

    def de_serialize(self, obj=None):
        """
        Creates a database object from a pydantic object
        """
        is_update = True
        if not obj:
            is_update = False
            obj = self.__model__()
        database_fields = self.get_database_mapping()
        meta = {}
        dump = self.model_dump(mode="json", exclude_defaults=True)
        for field in dump:
            if (
                field in database_fields
                and field not in self.__exclude__
                and field not in ["id", "external_id"]
            ):
                obj.__setattr__(field, dump[field])
            elif field not in self.__exclude__:
                meta[field] = dump[field]
        obj.meta = meta
        self.perform_extra_deserialization(is_update, obj)
        return obj

    @classmethod
    def as_questionnaire(cls, parent_classes=None):  # noqa PLR0912
        """
        This is created so that the FE has an idea about bound valuesets and other metadata about the form
        Maybe we can speed up this process by starting with model's JSON Schema
        Pydantic provides that by default for all models
        """
        if not parent_classes:
            parent_classes = []
        if cls.__questionnaire_cache__:
            return cls.__questionnaire_cache__
        questionnire_obj = []
        for field in cls.model_fields:
            field_class = cls.model_fields[field]
            field_obj = {"linkId": field}
            field_type = field_class.annotation

            if type(field_type) is UnionType:
                field_type = field_type.__args__[0]

            if get_origin(field_type) is list:
                field_obj["repeats"] = True
                field_type = field_type.__args__[0]

            if field_type in parent_classes:
                # Avoiding circular references
                continue

            if issubclass(field_type, Enum):
                field_obj["type"] = "string"
                field_obj["answer_options"] = [{x.name: x.value} for x in field_type]
            elif issubclass(field_type, datetime.datetime):
                field_obj["type"] = "dateTime"
            elif issubclass(field_type, str):
                field_obj["type"] = "string"
            elif issubclass(field_type, int):
                field_obj["type"] = "integer"
            elif issubclass(field_type, uuid.UUID):
                field_obj["type"] = "string"
            elif field_type is Coding:
                field_obj["type"] = "coding"
                field_obj["valueset"] = {"slug": field_class.json_schema_extra["slug"]}
            elif issubclass(field_type, EMRResource):
                field_obj["type"] = "group"
                parent_classes = parent_classes[::]
                parent_classes.append(cls)
                field_obj["questions"] = field_type.as_questionnaire(parent_classes)
            questionnire_obj.append(field_obj)
        cls.__questionnaire_cache__ = questionnire_obj
        return questionnire_obj

    def to_json(self):
        return self.model_dump(mode="json", exclude=["meta"])


PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber()],  # noqa: UP007
    PhoneNumberValidator(
        default_region=None,
        supported_regions=[],
        number_format="E164",
    ),
]
