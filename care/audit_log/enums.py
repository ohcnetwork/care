from enum import Enum


class Operation(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


DjangoOperations = [(e.value, o.lower()) for o, e in Operation.__members__.items()]
