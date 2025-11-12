from enum import Enum

from pydantic import BaseModel

from odoo.resource.product_category.spec import CategoryData


class TaxData(BaseModel):
    tax_name: str
    tax_percentage: float


class ProductStatus(str, Enum):
    active = "active"
    retired = "retired"
    draft = "draft"


class ProductData(BaseModel):
    product_name: str
    x_care_id: str
    cost: float
    mrp: float
    category: CategoryData
    taxes: list[TaxData] | None = None
    hsn: str | None = None
    status: ProductStatus
