from pydantic_core import CoreSchema, core_schema

from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.common import Coding


class ValueSetBoundCoding:
    @classmethod
    def __class_getitem__(cls, slug: str) -> type:
        class BoundCoding(Coding):
            @classmethod
            def __get_pydantic_core_schema__(cls, source_type, handler) -> CoreSchema:
                return core_schema.no_info_after_validator_function(
                    function=cls.validate_input, schema=handler(source_type), ref=slug
                )

            @classmethod
            def validate_input(cls, v):
                if isinstance(v, dict):
                    v = Coding.model_validate(v)
                return validate_valueset("code", slug, v)

        return BoundCoding
