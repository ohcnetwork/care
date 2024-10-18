from authlib.jose import jwt
from django.conf import settings
from django.utils.timezone import now


def generate_jwt(claims=None, exp=60, jwks=None):
    if claims is None:
        claims = {}
    if jwks is None:
        jwks = settings.JWKS
    header = {"alg": "RS256"}
    time = int(now().timestamp())
    payload = {
        "iat": time,
        "exp": time + exp,
        **claims,
    }
    return jwt.encode(header, payload, jwks).decode("utf-8")
