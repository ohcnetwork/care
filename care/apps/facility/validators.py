from django.core.validators import RegexValidator

vehicle_number_regex = RegexValidator(
    regex="^[A-Z]{2}[0-9]{1,2}[A-Z]{0,2}[0-9]{1,4}$",
    message="Please Enter the vehicle number in all uppercase without spaces, eg: KL13AB1234",
    code="invalid_vehicle_number",
)
