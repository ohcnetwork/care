import enum


class AvailabilityStatus(enum.Enum):
    NOT_MONITORED = 0
    OPERATIONAL = 1
    DOWN = 2
    UNDER_MAINTENANCE = 3
