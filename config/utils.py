from datetime import datetime

from authlib.jose import jwt
from django.conf import settings


def get_psql_search_tokens(text, operator="&"):
    return f" {operator} ".join([f"{word}:*" for word in text.strip().split(" ")])


def generate_jwt(claims=None, exp=60):
    if claims is None:
        claims = {}
    header = {"alg": "RS256"}
    time = int(datetime.now().timestamp())
    payload = {
        "iat": time,
        "exp": time + exp,
        **claims,
    }
    return jwt.encode(header, payload, settings.JWKS)
