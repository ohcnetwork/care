from django.test import TestCase

from care.utils.registries.feature_flag import FlagNotFoundError, FlagRegistry, FlagType


# ruff: noqa: SLF001
class FeatureFlagTestCase(TestCase):
    def setUp(self):
        FlagRegistry._flags = {}
        super().setUp()

    def test_register_flag(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        self.assertTrue(FlagRegistry._flags[FlagType.USER]["TEST_FLAG"])
        FlagRegistry.register(FlagType.USER, "TEST_FLAG_2")
        self.assertTrue(FlagRegistry._flags[FlagType.USER]["TEST_FLAG_2"])

    def test_unregister_flag(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        self.assertTrue(FlagRegistry._flags[FlagType.USER]["TEST_FLAG"])
        FlagRegistry.unregister(FlagType.USER, "TEST_FLAG")
        self.assertFalse(FlagRegistry._flags[FlagType.USER].get("TEST_FLAG"))

    def test_validate_flag_type(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        self.assertIsNone(FlagRegistry.validate_flag_type(FlagType.USER))

    def test_validate_flag_type_invalid(self):
        with self.assertRaises(FlagNotFoundError):
            FlagRegistry.validate_flag_type(
                FlagType.USER
            )  # FlagType.USER is not registered

    def test_validate_flag_name(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        self.assertIsNone(FlagRegistry.validate_flag_name(FlagType.USER, "TEST_FLAG"))

    def test_validate_flag_name_invalid(self):
        with self.assertRaises(FlagNotFoundError) as ectx:
            FlagRegistry.validate_flag_name(FlagType.USER, "TEST_OTHER_FLAG")
        self.assertEqual(ectx.exception.message, "Invalid Flag Type")

        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        with self.assertRaises(FlagNotFoundError) as ectx:
            FlagRegistry.validate_flag_name(FlagType.USER, "TEST_OTHER_FLAG")
        self.assertEqual(ectx.exception.message, "Flag not registered")

    def test_get_all_flags(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        FlagRegistry.register(FlagType.USER, "TEST_FLAG_2")
        self.assertEqual(
            FlagRegistry.get_all_flags(FlagType.USER), ["TEST_FLAG", "TEST_FLAG_2"]
        )

    def test_get_all_flags_as_choices(self):
        FlagRegistry.register(FlagType.USER, "TEST_FLAG")
        FlagRegistry.register(FlagType.USER, "TEST_FLAG_2")
        self.assertEqual(
            list(FlagRegistry.get_all_flags_as_choices(FlagType.USER)),
            [("TEST_FLAG", "TEST_FLAG"), ("TEST_FLAG_2", "TEST_FLAG_2")],
        )
