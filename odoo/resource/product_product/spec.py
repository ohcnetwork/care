from enum import Enum

from pydantic import BaseModel

from odoo.resource.product_category.spec import CategoryData


class TaxType(str, Enum):
    purchase_tax = "purchase_tax"
    sale_tax = "sale_tax"


class TaxData(BaseModel):
    tax_type: TaxType
    tax_name: str
    tax_percentage: float


class ProductData(BaseModel):
    product_name: str
    x_care_id: str
    cost: float
    mrp: float
    category: CategoryData
    taxes: list[TaxData] | None = None
