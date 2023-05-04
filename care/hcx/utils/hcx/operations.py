import enum


class HcxOperations(enum.Enum):
    COVERAGE_ELIGIBILITY_CHECK = "/coverageeligibility/check"
    COVERAGE_ELIGIBILITY_ON_CHECK = "/coverageeligibility/on_check"
    PRE_AUTH_SUBMIT = "/preauth/submit"
    PRE_AUTH_ON_SUBMIT = "/preauth/on_submit"
    CLAIM_SUBMIT = "/claim/submit"
    CLAIM_ON_SUBMIT = "/claim/on_submit"
    PAYMENT_NOTICE_REQUEST = "/paymentnotice/request"
    PAYMENT_NOTICE_ON_REQUEST = "/paymentnotice/on_request"
    HCX_STATUS = "/hcx/status"
    HCX_ON_STATUS = "/hcx/on_status"
    COMMUNICATION_REQUEST = "/communication/request"
    COMMUNICATION_ON_REQUEST = "/communication/on_request"
    PREDETERMINATION_SUBMIT = "/predetermination/submit"
    PREDETERMINATION_ON_SUBMIT = "/predetermination/on_submit"

    def __str__(self):
        return "%s" % self.value
