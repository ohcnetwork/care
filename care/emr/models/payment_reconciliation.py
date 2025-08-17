from django.db import models

from care.emr.models import EMRBaseModel


class PaymentReconciliation(EMRBaseModel):
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    target_invoice = models.ForeignKey(
        "emr.Invoice", on_delete=models.PROTECT, null=True, blank=True, default=None
    )
    account = models.ForeignKey("emr.Account", on_delete=models.PROTECT)
    reconciliation_type = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    kind = models.CharField(max_length=100)
    issuer_type = models.CharField(max_length=100)
    outcome = models.CharField(max_length=100)
    disposition = models.TextField(null=True, blank=True)
    payment_datetime = models.DateTimeField(null=True, blank=True)
    method = models.CharField(max_length=100)
    reference_number = models.CharField(max_length=1024, null=True, blank=True)
    authorization = models.CharField(max_length=1024, null=True, blank=True)
    tendered_amount = models.DecimalField(max_digits=10, decimal_places=2)
    returned_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(null=True, blank=True)
