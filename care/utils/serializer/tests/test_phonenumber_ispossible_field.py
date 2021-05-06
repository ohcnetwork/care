from unittest import TestCase

from rest_framework.exceptions import ValidationError

from care.utils.serializer.phonenumber_ispossible_field import PhoneNumberIsPossibleField


class TestPhoneNumberIsPossibleField(TestCase):
    def test_phone_number(self):
        # map -> input value -> output value
        # if output value is None, the it is invalid

        test_cases = {
            "7795937091": "+917795937091",
            "07795937091": "+917795937091",
            "+917795937091": "+917795937091",
            "+1 470-485-8757": "+14704858757",
            "+18944775567": "+18944775567",
            "+911234": None,
        }

        for ip, op in test_cases.items():
            if op is None:
                with self.assertRaises(ValidationError):
                    PhoneNumberIsPossibleField().to_internal_value(ip)
            else:
                self.assertEqual(PhoneNumberIsPossibleField().to_internal_value(ip), op)
