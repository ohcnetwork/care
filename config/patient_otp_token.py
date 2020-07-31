from rest_framework_simplejwt.tokens import Token

from datetime import timedelta


class PatientToken(Token):
    lifetime = timedelta(hours=1)
    token_type = "patient_login"
