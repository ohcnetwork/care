from django.core.management.base import BaseCommand

from care.utils.jwks.generate_jwk import generate_encoded_jwks


class Command(BaseCommand):
    """
    Generate JWKS
    """

    help = "Generate JWKS"

    def handle(self, *args, **options):
        print(generate_encoded_jwks())
