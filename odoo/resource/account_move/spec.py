from enum import Enum

from pydantic import BaseModel, Field

from odoo.resource.product_product.spec import ProductData
from odoo.resource.res_partner.spec import PartnerData


class DiscountGroup(BaseModel):
    x_care_id: str
    name: str


class DiscountType(str, Enum):
    amount = "amount"
    factor = "factor"


class InvoiceDiscounts(BaseModel):
    name: str
    discount_group: DiscountGroup
    discount_type: DiscountType
    rate: float = 0.0
    disc_amt: float = 0.0


class AgentData(BaseModel):
    x_care_id: str


class InvoiceItem(BaseModel):
    product_data: ProductData
    quantity: str = Field(default="1.0")
    sale_price: str = Field(default="0.0")
    x_care_id: str
    agent_id: str | None = None
    discounts: InvoiceDiscounts | None = None


class BillType(str, Enum):
    vendor = "vendor"
    customer = "customer"


class AccountMoveApiRequest(BaseModel):
    x_care_id: str
    bill_type: BillType
    invoice_date: str
    due_date: str
    partner_data: PartnerData
    invoice_items: list[InvoiceItem]
    reason: str


class AccountMoveReturnApiRequest(BaseModel):
    x_care_id: str
    bill_type: BillType | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    partner_data: PartnerData | None = None
    invoice_items: list[InvoiceItem] | None = None
    reason: str
