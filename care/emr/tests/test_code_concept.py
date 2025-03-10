import unittest

from care.emr.fhir.resources.code_concept import CodeConceptResource


class TestCodeConceptResource(unittest.TestCase):
    def setUp(self):
        self.resource = CodeConceptResource()
        self.resource._filters = {"system": "test_system", "code": "test_code"}  # noqa SLF001

    def test_get_no_results(self):
        self.resource.query = lambda method, endpoint, filters: {}

        with self.assertRaises(ValueError) as context:
            self.resource.get()

        self.assertEqual(
            str(context.exception), "No results found for the given system and code"
        )
