from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseOutputGenerator(ABC):
    options_model = BaseOptions

    @abstractmethod
    def generate(self, html: str, options: dict[str, Any] | None = None) -> bytes:
        pass

    @abstractmethod
    def get_format(self) -> str:
        pass

    def get_supported_options(self) -> dict[str, Any]:
        return {}

    @abstractmethod
    def get_http_response(self, response):
        pass
