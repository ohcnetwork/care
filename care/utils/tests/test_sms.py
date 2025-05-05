from io import StringIO
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.test import TestCase, override_settings

from care.utils.sms import send_text_message


@override_settings(
    SMS_BACKEND="care.utils.sms.backend.sns.SnsBackend",
    SNS_REGION="us-east-1",
    SNS_ACCESS_KEY="fake_access_key",
    SNS_SECRET_KEY="fake_secret_key",
    SNS_ROLE_BASED_MODE=False,
)
class TestSendTextMessage(TestCase):
    @patch("care.utils.sms.backend.sns.SnsBackend._get_client")
    def test_send_to_single_recipient(self, mock_get_client):
        """Sending an SMS to one recipient should call publish once and return 1."""
        mock_sns_client = MagicMock()
        mock_get_client.return_value = mock_sns_client

        sent_count = send_text_message(
            content="Hello, world!",
            recipients="+10000000000",
        )

        self.assertEqual(sent_count, 1)
        mock_sns_client.publish.assert_called_once_with(
            PhoneNumber="+10000000000",
            Message="Hello, world!",
        )

    @patch("care.utils.sms.backend.sns.SnsBackend._get_client")
    def test_send_to_multiple_recipients(self, mock_get_client):
        """Sending an SMS to multiple recipients should call publish per recipient."""
        mock_sns_client = MagicMock()
        mock_get_client.return_value = mock_sns_client

        recipients = ["+10000000000", "+20000000000"]
        sent_count = send_text_message(
            content="Group message",
            recipients=recipients,
        )

        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_sns_client.publish.call_count, 2)

    @patch("care.utils.sms.backend.sns.SnsBackend._get_client")
    def test_fail_silently_false_raises_error(self, mock_get_client):
        """If publish fails and fail_silently=False, a ClientError should be raised."""
        mock_sns_client = MagicMock()
        mock_sns_client.publish.side_effect = ClientError(
            {"Error": {"Code": "MockError"}}, "Publish"
        )
        mock_get_client.return_value = mock_sns_client

        with self.assertRaises(ClientError):
            send_text_message(
                content="Failing message",
                recipients=["+30000000000"],
                fail_silently=False,
            )

    @patch("care.utils.sms.backend.sns.SnsBackend._get_client")
    def test_fail_silently_true_swallows_error(self, mock_get_client):
        """If publish fails but fail_silently=True, no error should be raised."""
        mock_sns_client = MagicMock()
        mock_sns_client.publish.side_effect = ClientError(
            {"Error": {"Code": "MockError"}}, "Publish"
        )
        mock_get_client.return_value = mock_sns_client

        sent_count = send_text_message(
            content="Silently failing message",
            recipients=["+40000000000"],
            fail_silently=True,
        )

        self.assertEqual(sent_count, 0, "Should report 0 messages sent on failure")
        self.assertEqual(mock_sns_client.publish.call_count, 1)


@override_settings(
    SMS_BACKEND="care.utils.sms.backend.console.ConsoleBackend",
)
class TestTextMessageWithConsoleBackend(TestCase):
    """
    Tests sending SMS via the ConsoleBackend, which writes messages to stdout.
    """

    @patch("sys.stdout", new_callable=StringIO)
    def test_send_single_recipient(self, mock_stdout):
        """
        Verifies a single message to one recipient is printed correctly
        and returns a successful send count of 1.
        """
        sent_count = send_text_message(
            content="Hello via Console!",
            recipients="+10000000000",
        )
        self.assertEqual(sent_count, 1, "Should report 1 for one successful send")

        output = mock_stdout.getvalue()
        self.assertIn("Hello via Console!", output)
        self.assertIn("+10000000000", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_send_multiple_recipients(self, mock_stdout):
        """
        Verifies multiple messages are printed for multiple recipients
        and that send_text_message reports the correct count.
        """
        recipients = ["+20000000000", "+30000000000"]
        sent_count = send_text_message(
            content="Group console message",
            recipients=recipients,
        )
        self.assertEqual(sent_count, 2, "Should report 2 for two successful sends")

        output = mock_stdout.getvalue()
        self.assertIn("Group console message", output)
        for r in recipients:
            self.assertIn(r, output)
