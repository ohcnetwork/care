from pydantic import BaseModel


class CategoryData(BaseModel):
    category_name: str
    parent_x_care_id: str
    x_care_id: str
