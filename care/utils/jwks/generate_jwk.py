import base64
import json
from pathlib import Path

from authlib.jose import JsonWebKey


def generate_encoded_jwks():
    key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    key = key.as_dict(key.dumps_private_key(), alg="RS256")

    keys = {"keys": [key]}
    keys_json = json.dumps(keys)
    return base64.b64encode(keys_json.encode()).decode()


def get_jwks_from_file(base_path: Path):
    file_path = base_path / "jwks.b64.txt"
    try:
        with open(file_path) as file:
            return file.read()
    except FileNotFoundError:
        jwks = generate_encoded_jwks()
        with open(file_path, "w") as file:
            file.write(jwks)
        return jwks
