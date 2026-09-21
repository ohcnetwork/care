import base64
import json
from types import SimpleNamespace

from altcha import Payload, create_challenge, solve_challenge
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APITestCase

from config.auth_views import CaptchaRequiredException
from config.ratelimit import validatecaptcha


class AltchaTestCase(APITestCase):
    def setUp(self):
        cache.clear()

    def create_payload(self):
        challenge = create_challenge(
            algorithm="PBKDF2/SHA-256",
            cost=100,
            hmac_secret=settings.ALTCHA_HMAC_SECRET,
        )
        return Payload(challenge, solve_challenge(challenge)).to_base64()

    def test_challenge_is_not_cached(self):
        response = self.client.get("/api/v1/auth/captcha/challenge/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])

    def test_solution_can_only_be_used_once(self):
        payload = self.create_payload()

        first_request = SimpleNamespace(data={"altcha": payload})
        replay_request = SimpleNamespace(data={"altcha": payload})

        self.assertTrue(validatecaptcha(first_request))
        self.assertTrue(validatecaptcha(first_request))
        self.assertFalse(validatecaptcha(replay_request))

    def test_malformed_solution_is_rejected(self):
        request = SimpleNamespace(data={"altcha": "invalid"})

        self.assertFalse(validatecaptcha(request))

    def test_invalid_counter_is_rejected(self):
        payload = json.loads(base64.b64decode(self.create_payload()))
        payload["solution"]["counter"] = -1
        encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode()

        self.assertFalse(
            validatecaptcha(SimpleNamespace(data={"altcha": encoded_payload}))
        )

    def test_captcha_required_error_has_stable_code(self):
        exception = CaptchaRequiredException(
            detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
            code="captchaRequired",
        )

        self.assertEqual(exception.detail["code"], "captchaRequired")
