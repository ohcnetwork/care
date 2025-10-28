from pydantic import BaseModel

from odoo.resource.product_category.spec import CategoryData


class ProductData(BaseModel):
    product_name: str
    x_care_id: str
    cost: str
    mrp: str
    category: CategoryData
