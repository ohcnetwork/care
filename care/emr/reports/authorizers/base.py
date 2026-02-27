from abc import ABC, abstractmethod


class BaseReportAuthorizer(ABC):
    @abstractmethod
    def authorize_read(self, user, associating_id: str) -> bool:
        pass

    @abstractmethod
    def authorize_write(self, user, associating_id: str) -> bool:
        pass
