from cryptography.fernet import Fernet
from django.conf import settings

_fernet = Fernet(settings.TOTP_SECRET_ENCRYPTION_KEY.encode())


def encrypt_string(text: str) -> str:
    """Encrypt a string using Fernet."""
    return _fernet.encrypt(text.encode()).decode()


def decrypt_string(encrypted_text: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    return _fernet.decrypt(encrypted_text.encode()).decode()
