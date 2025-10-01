from enum import Enum

DEFAULT_FAVORITE_LIST = "default"


class FavoriteResourceChoices(str, Enum):
    activity_definition = "activity_definition"
    charge_item_definition = "charge_item_definition"
    product_knowledge = "product_knowledge"
    observation_definition = "observation_definition"
