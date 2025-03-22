from care.emr.registries.care_valueset.care_valueset import validate_valueset
from care.emr.resources.common import Coding


class ValueSetBoundCoding:
    @classmethod
    def __class_getitem__(cls, slug: str):
        class BoundCoding(Coding):
            @classmethod
            def __get_validators__(cls):
                yield cls.validate_input

            @classmethod
            def validate_input(cls, v):
                if isinstance(v, dict):
                    v = Coding.model_validate(v)
                return validate_valueset("code", slug, v)

        return BoundCoding
