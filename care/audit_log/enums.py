from enum import Enum


class Operation(int, Enum):
    INSERT = 1
    UPDATE = 0
    DELETE = -1


DjangoOperations = [(e.value, o.lower()) for o, e in Operation.__members__.items()]
