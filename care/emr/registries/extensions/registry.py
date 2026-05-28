class ExtensionRegistry:
    _extensions = {}

    @classmethod
    def register(cls, extension_obj) -> None:
        from care.emr.extensions.base import ExtensionBase

        if not issubclass(extension_obj.__class__, ExtensionBase):
            raise ValueError("The provided class is not a subclass of ExtensionBase")
        if not extension_obj.resource_type or not extension_obj.extension_name:
            raise ValueError("Resource type and extension name are required")
        if extension_obj.resource_type.value not in cls._extensions:
            cls._extensions[extension_obj.resource_type.value] = {}
        cls._extensions[extension_obj.resource_type.value][
            extension_obj.extension_name
        ] = extension_obj

    @classmethod
    def get_extension_obj(cls, resource_type, extension_name):
        if (
            resource_type not in cls._extensions
            or extension_name not in cls._extensions[resource_type]
        ):
            return None
        return cls._extensions[resource_type][extension_name]

    @classmethod
    def get_extensions(cls):
        return cls._extensions

    @classmethod
    def get_extensions_for_resource(cls, resource_type):
        return cls._extensions.get(resource_type, {})
