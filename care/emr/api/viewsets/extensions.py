from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet
from care.emr.registries.extensions.registry import ExtensionRegistry


class ExtensionsViewSet(EMRBaseViewSet):
    def serialize_extension(self, extension):
        return {
            "name": extension.extension_name,
            "owner": extension.extension_owner.value,
            "version": extension.extension_version,
            "write_schema": extension.get_write_schema(),
            "read_schema": extension.get_read_schema(),
            "retrieve_schema": extension.get_retrieve_schema(),
        }

    def serialize_extensions(self, extensions):
        return [
            self.serialize_extension(extension) for _, extension in extensions.items()
        ]

    def list(self, request, *args, **kwargs):
        registry = ExtensionRegistry()
        extensions = registry.get_extensions()
        data = {}
        for resource_type, resource_extensions in extensions.items():
            data[resource_type] = self.serialize_extensions(resource_extensions)
        return Response(data)
