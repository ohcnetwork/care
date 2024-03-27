import unittest.mock as mock

import boto3
from django.test import TestCase, override_settings
from sms import send_sms


class CustomSMSBackendSNSTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

    @override_settings(
        SNS_ACCESS_KEY="dummy-access-key",
        SNS_SECRET_KEY="dummy-secret-key",
        SNS_REGION="dummy-region",
        SMS_BACKEND="care.utils.sms.sendSMS.CustomSMSBackendSNS",
    )
    def test_send_sms(self):
        mock_sns_client = mock.MagicMock()  # Create a mock SNS client
        mock_sns_client.publish.return_value = 2  # Set return value for publish
        phone_numbers = ["+1234567890", "+1987654321"]
        message_body = "Hello, this is a test SMS message!"

        with mock.patch.object(boto3, "client", return_value=mock_sns_client):
            send_sms(
                body=message_body,
                recipients=phone_numbers,
            )

            mock_sns_client.publish.assert_has_calls(
                [
                    mock.call(PhoneNumber="+1234567890", Message=message_body),
                    mock.call(PhoneNumber="+1987654321", Message=message_body),
                ]
            )
