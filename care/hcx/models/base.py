def reverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[0]] = choice[1]
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
