import json
from enum import Enum
from os import getenv

from jsonschema import validate

from care.emr.registries.extensions.registry import ExtensionRegistry


class ExtensionResource(str, Enum):
    account = "account"
    encounter = "encounter"
    patient = "patient"
    payment_reconciliation = "payment_reconciliation"
    supply_delivery = "supply_delivery"
    supply_delivery_order = "supply_delivery_order"
    product = "product"


class ExtensionOwners(str, Enum):
    core = "core"
    plug = "plug"


class ExtensionBase:
    resource_type: ExtensionResource

    extension_name = ""

    write_schema = ""
    read_schema = ""
    retrieve_schema = ""

    extension_owner: ExtensionOwners = ExtensionOwners.core

    extension_version = ""

    def get_read_schema(self):
        return self.read_schema

    def get_write_schema(self):
        return self.write_schema

    def get_retrieve_schema(self):
        return self.retrieve_schema

    def validate(self, data, resource=None):
        pass

    def serialize_extensions(self, data, resource=None):
        return data

    def deserialize_extensions_list(self, data, resource):
        pass

    def deserialize_extensions_retrieve(self, data, resource):
        pass


class CoreEnvExtension(ExtensionBase):
    """
    Loads core extensions from environment variable
    """

    extension_name = "core"

    def schema_key(self, action):
        return f"CORE_EXTENSIONS_{self.resource_type.value.upper()}_{action}"

    def get_env_value(self, key):
        if not getenv(key):
            return {}
        try:
            return json.loads(getenv(key))
        except Exception as e:
            raise ValueError("Invalid JSON") from e

    def get_write_schema(self):
        return self.get_env_value(self.schema_key("WRITE"))

    def get_read_schema(self):
        return self.get_env_value(self.schema_key("READ")) or self.get_write_schema()

    def get_retrieve_schema(self):
        return self.get_env_value(self.schema_key("RETRIEVE")) or self.get_read_schema()

    def validate(self, data, resource=None):
        write_schema = self.get_write_schema()
        try:
            validate(data, write_schema)
        except Exception as e:
            raise ValueError("Invalid Data") from e
        return data

    def serialize_extensions(self, data, resource=None):
        return data

    def deserialize_extensions_list(self, data, resource):
        return data

    def deserialize_extensions_retrieve(self, data, resource):
        return data


class PlugExtension(ExtensionBase):
    extension_owner: ExtensionOwners = ExtensionOwners.plug

    def serialize_extensions(self, data, resource=None):
        return data

    def deserialize_extensions_list(self, data, resource):
        return data

    def deserialize_extensions_retrieve(self, data, resource):
        return data


for resource_type in ExtensionResource:
    extension_obj = CoreEnvExtension()
    extension_obj.resource_type = resource_type
    ExtensionRegistry.register(extension_obj)


# TODO: Support for definitions, core overrides everything and maintains a list.
# TODO: Lock the schema version to something, override for all schems, plug and core.
# TODO: Support rendering extensions through the de-serialization methods.
