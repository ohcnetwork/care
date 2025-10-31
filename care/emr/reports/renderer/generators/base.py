from abc import ABC, abstractmethod
from typing import Any


class BaseOutputGenerator(ABC):
    @abstractmethod
    def generate(self, html: str, options: dict[str, Any] | None = None) -> bytes:
        pass

    @abstractmethod
    def get_format(self) -> str:
        pass

    def get_supported_options(self) -> dict[str, Any]:
        return {}
