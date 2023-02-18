def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


# http://hl7.org/fhir/fm-status
STATUS_CHOICES = [
    ("active", "Active"),
    ("cancelled", "Cancelled"),
    ("draft", "Draft"),
    ("entered-in-error", "Entered in Error"),
]
REVERSE_STATUS_CHOICES = reverse_choices(STATUS_CHOICES)


# http://terminology.hl7.org/CodeSystem/processpriority
PRIORITY_CHOICES = [
    ("stat", "Immediate"),
    ("normal", "Normal"),
    ("deferred", "Deferred"),
]
REVERSE_PRIORITY_CHOICES = reverse_choices(PRIORITY_CHOICES)


# http://hl7.org/fhir/eligibilityrequest-purpose
PURPOSE_CHOICES = [
    ("auth-requirements", "Auth Requirements"),
    ("benefits", "Benefits"),
    ("discovery", "Discovery"),
    ("validation", "Validation"),
]
REVERSE_PURPOSE_CHOICES = reverse_choices(PURPOSE_CHOICES)


# http://hl7.org/fhir/remittance-outcome
OUTCOME_CHOICES = [
    ("queued", "Queued"),
    ("complete", "Processing Complete"),
    ("error", "Error"),
    ("partial", "Partial Processing"),
]
REVERSE_OUTCOME_CHOICES = reverse_choices(OUTCOME_CHOICES)

# http://hl7.org/fhir/claim-use
USE_CHOICES = [
    ("claim", "Claim"),
    ("preauthorization", "Pre-Authorization"),
    ("predetermination", "Pre-Determination"),
]
REVERSE_USE_CHOICES = reverse_choices(USE_CHOICES)

# http://hl7.org/fhir/claim-use
CLAIM_TYPE_CHOICES = [
    ("institutional", "Institutional"),
    ("oral", "Oral"),
    ("pharmacy", "Pharmacy"),
    ("professional", "Professional"),
    ("vision", "Vision"),
]
REVERSE_CLAIM_TYPE_CHOICES = reverse_choices(CLAIM_TYPE_CHOICES)
