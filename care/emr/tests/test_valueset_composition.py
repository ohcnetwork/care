from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from care.emr.models.valueset import ValueSet


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)
class TestValueSetComposition(SimpleTestCase):
    @patch("care.emr.fhir.client.FHIRClient.query", return_value={"expansion": {}})
    def test_expansion_preserves_includes_and_excludes_across_inheritance(self, query):
        system = "http://snomed.info/sct"

        def valueset(include=(), exclude=(), **kwargs):
            return ValueSet(
                compose={
                    "include": [
                        {"system": system, "concept": [{"code": code}]}
                        for code in include
                    ],
                    "exclude": [
                        {"system": system, "concept": [{"code": code}]}
                        for code in exclude
                    ],
                },
                **kwargs,
            )

        cases = [
            (
                "same system in one set",
                valueset(["included"], ["excluded"]),
                ["included"],
                ["excluded"],
            ),
            (
                "child excludes from parent inclusion",
                valueset(exclude=["excluded"], parent=valueset(["included"])),
                ["included"],
                ["excluded"],
            ),
            (
                "parent excludes from child inclusion",
                valueset(["included"], parent=valueset(exclude=["excluded"])),
                ["included"],
                ["excluded"],
            ),
            (
                "disabled inheritance keeps local composition",
                valueset(
                    ["included"],
                    ["excluded"],
                    parent=valueset(["parent-included"], ["parent-excluded"]),
                    disable_composition=True,
                ),
                ["included"],
                ["excluded"],
            ),
        ]
        without_exclusions = valueset(["included"])
        without_exclusions.compose.pop("exclude")
        cases.append(
            ("optional exclusions omitted", without_exclusions, ["included"], [])
        )

        for label, instance, expected_include, expected_exclude in cases:
            with self.subTest(label):
                query.reset_mock()
                instance.search()
                query.assert_called_once()
                self.assertEqual(query.call_args.kwargs["resource"], "ValueSet/$expand")
                parameters = query.call_args.kwargs["parameters"]["parameter"]
                composition = next(
                    parameter["resource"]["compose"]
                    for parameter in parameters
                    if parameter["name"] == "valueSet"
                )
                for key, expected in (
                    ("include", expected_include),
                    ("exclude", expected_exclude),
                ):
                    self.assertEqual(
                        [
                            concept["code"]
                            for entry in composition[key]
                            for concept in entry["concept"]
                        ],
                        expected,
                    )
                    self.assertTrue(
                        all(entry["system"] == system for entry in composition[key])
                    )
