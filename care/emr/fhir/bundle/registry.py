"""
FHIR Resource Processor Registry.

This module provides a registry for FHIR resource processors, enabling
extensibility by allowing new processors to be registered dynamically.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from care.emr.fhir.bundle.base import FHIRResourceProcessor

logger = logging.getLogger(__name__)


class FHIRResourceRegistry:
    """
    Registry for FHIR resource processors.

    This registry maintains a mapping of FHIR resource types to their
    corresponding processor classes. It provides methods to register
    and retrieve processors.

    Usage:
        # Register a processor
        FHIRResourceRegistry.register(ConditionProcessor)

        # Get a processor class
        processor_class = FHIRResourceRegistry.get("Condition")

        # List supported resource types
        supported = FHIRResourceRegistry.get_supported_types()
    """

    _processors: dict[str, type["FHIRResourceProcessor"]] = {}

    @classmethod
    def register(cls, processor_class: type["FHIRResourceProcessor"]) -> None:
        """
        Register a processor class for a FHIR resource type.

        Args:
            processor_class: The processor class to register

        Raises:
            ValueError: If the processor doesn't have a resource_type
        """
        if not processor_class.resource_type:
            raise ValueError(
                f"Processor {processor_class.__name__} must define a resource_type"
            )

        resource_type = processor_class.resource_type
        if resource_type in cls._processors:
            logger.warning(
                f"Overwriting existing processor for resource type: {resource_type}"
            )

        cls._processors[resource_type] = processor_class
        logger.debug(f"Registered processor for resource type: {resource_type}")

    @classmethod
    def get(cls, resource_type: str) -> type["FHIRResourceProcessor"] | None:
        """
        Get the processor class for a FHIR resource type.

        Args:
            resource_type: The FHIR resource type (e.g., "Condition")

        Returns:
            The processor class or None if not registered
        """
        return cls._processors.get(resource_type)

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get a list of all supported FHIR resource types.

        Returns:
            List of supported resource type names
        """
        return list(cls._processors.keys())

    @classmethod
    def is_supported(cls, resource_type: str) -> bool:
        """
        Check if a resource type is supported.

        Args:
            resource_type: The FHIR resource type

        Returns:
            True if the resource type has a registered processor
        """
        return resource_type in cls._processors

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered processors.

        This is primarily useful for testing.
        """
        cls._processors.clear()


def register_processor(processor_class: type["FHIRResourceProcessor"]):
    """
    Decorator to register a processor class with the registry.

    Usage:
        @register_processor
        class ConditionProcessor(FHIRResourceProcessor):
            resource_type = "Condition"
            ...

    Args:
        processor_class: The processor class to register

    Returns:
        The processor class (unchanged)
    """
    FHIRResourceRegistry.register(processor_class)
    return processor_class
