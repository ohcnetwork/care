from enum import Enum

from pydantic import BaseModel

from odoo.resource.res_partner.spec import PartnerData


class JournalType(str, Enum):
    cash = "cash"
    bank = "bank"


class PartnerType(str, Enum):
    vendor = "vendor"
    customer = "customer"


class AccountMovePaymentApiRequest(BaseModel):
    x_care_id: str
    journal_x_care_id: str
    amount: float = 0.0
    journal_input: JournalType
    payment_date: str
    partner_type: PartnerType
    partner_data: PartnerData
