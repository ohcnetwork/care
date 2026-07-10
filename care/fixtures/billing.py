from datetime import timedelta

from django.utils import timezone

from care.emr.models.charge_item_definition import ChargeItemDefinition

# Number of patients (and accounts) the billing seed spreads invoices across.
BILLING_ACCOUNTS = 2

# Populates invoice numbers, e.g. "#INV-100-26", "#INV-101-26", ...
# The expression is evaluated as a Python f-string literal.
INVOICE_NUMBER_EXPRESSION = "f'#INV-{invoice_count + 100}-{current_year_yy}'"

# Invoice plan: (created_date offset in days, [(cid_title, quantity), ...], status).
# Charge items are built from existing charge item definitions (lab tests,
# medicines, consumables) so each links back to the catalogue. Dates are spread
# out so the invoice list date-range filter has data on both sides of any
# reasonable range, and every invoice status is represented (draft, issued,
# balanced, cancelled, entered_in_error).
INVOICE_PLAN = [
    (0, [("Complete Blood Count (CBC) Test", 1)], "draft"),
    (3, [("Paracetamol 500mg Tablet", 10)], "issued"),
    (7, [("Urinalysis Test", 1), ("Amoxicillin 500mg Capsule", 15)], "balanced"),
    (30, [("Lipid Panel Test", 1)], "issued"),
    (45, [("Fasting Blood Glucose Test", 1)], "cancelled"),
    (60, [("Ibuprofen 400mg Tablet", 20), ("Pair of Gloves", 2)], "balanced"),
    (75, [("Paracetamol 500mg Tablet", 5)], "entered_in_error"),
    (
        90,
        [
            ("Fasting Blood Glucose Test", 1),
            ("Complete Blood Count (CBC) Test", 1),
            ("Pair of Gloves", 5),
        ],
        "issued",
    ),
]


def load_billing(base, facility_id, patients, encounters=None):
    """Seed a comprehensive billing picture.

    For a couple of patients this creates:

    - an ``Account`` named ``"<FirstName> <YYYY-MM-DD>"``, tied to the patient's
      primary encounter,
    - ``ChargeItem`` line items built from existing charge item definitions
      (lab tests, medicines, consumables), performed by the seeding user,
    - ``Invoice`` records with generated numbers, spread across known
      ``created_date`` values, covering every status (draft, issued, balanced,
      cancelled, entered_in_error), and
    - ``PaymentReconciliation`` payments against the balanced invoices.

    ``created_date`` is backdated via an ORM update inside ``base.create_invoice``
    because the API stamps it to ``now`` on creation.
    """
    if len(patients) < BILLING_ACCOUNTS:
        return

    now = timezone.now()
    encounters = encounters or {}

    base.set_invoice_expression(facility_id, INVOICE_NUMBER_EXPRESSION)

    # Resolve charge item definition slugs by title (robust against slugify
    # quirks like "(CBC)" -> "cbc").
    cid_slugs = dict(
        ChargeItemDefinition.objects.filter(
            facility__external_id=facility_id
        ).values_list("title", "slug")
    )
    performer = str(base.user.external_id)

    accounts = []
    for patient in patients[:BILLING_ACCOUNTS]:
        first_name = patient.name.split()[0]
        account = base.create_account(
            facility_id,
            patient.id,
            name=f"{first_name} {now:%Y-%m-%d}",
        )
        encounter = encounters.get(patient.id)
        if encounter is not None:
            base.update_account(facility_id, account, primary_encounter=encounter.id)
        accounts.append((account, patient))

    for idx, (offset, items, status) in enumerate(INVOICE_PLAN):
        account, patient = accounts[idx % len(accounts)]
        # Only invoice items created by this apply call. Cancelled/error
        # invoices return older items to billable status on the same account.
        before = {ci.id for ci in base.list_charge_items(facility_id, account.id)}
        requests = [
            {
                "quantity": str(quantity),
                "charge_item_definition": cid_slugs[title],
                "patient": patient.id,
                "account": account.id,
                "performer_actor": performer,
            }
            for title, quantity in items
        ]
        base.apply_charge_item_defs(facility_id, requests)
        charge_item_ids = [
            charge_item.id
            for charge_item in base.list_charge_items(facility_id, account.id)
            if charge_item.id not in before
        ]
        created = now - timedelta(days=offset)
        invoice = base.create_invoice(
            facility_id,
            account.id,
            charge_item_ids,
            created_date=created,
        )

        if status == "draft":
            continue
        if status == "entered_in_error":
            base.cancel_invoice(facility_id, invoice, reason="entered_in_error")
            continue

        invoice = base.issue_invoice(
            facility_id, invoice, issue_date=created.isoformat()
        )
        if status == "issued":
            continue
        if status == "cancelled":
            base.cancel_invoice(facility_id, invoice, reason="cancelled")
            continue
        if status == "balanced":
            base.create_payment_reconciliation(
                facility_id,
                account.id,
                tendered_amount=str(invoice.total_gross),
                returned_amount=0,
                target_invoice=invoice.id,
                payment_datetime=created.isoformat(),
            )
            base.balance_invoice(facility_id, invoice)
