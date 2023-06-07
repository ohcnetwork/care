from datetime import timedelta

from rest_framework_simplejwt.tokens import Token


class PatientToken(Token):
    lifetime = timedelta(hours=1)
    token_type = "patient_login"
