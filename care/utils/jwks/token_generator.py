from authlib.jose import jwt
from django.conf import settings
from django.utils import timezone


def generate_jwt(claims=None, exp=60):
    if claims is None:
        claims = {}
    header = {"alg": "RS256"}
    time = int(timezone.now().timestamp())
    payload = {
        "iat": time,
        "exp": time + exp,
        **claims,
    }
    return jwt.encode(header, payload, settings.JWKS).decode("utf-8")
