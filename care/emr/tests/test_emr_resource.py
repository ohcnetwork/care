from django.test import SimpleTestCase

from care.emr.resources.base import EMRResource


class DummyEMRResource(EMRResource):
    pass


class DummyEMRResourceUpdate(EMRResource):
    _is_update = True


class DummyEMRResourceWithContext(EMRResource):
    _context = {"user": "test_user", "is_create": True}


class EMRResourceTestCase(SimpleTestCase):
    def test_is_update_returns_false_by_default(self):
        resource = DummyEMRResource()
        self.assertFalse(resource.is_update())

    def test_is_update_returns_true_when_set(self):
        resource = DummyEMRResourceUpdate()
        self.assertTrue(resource.is_update())

    def test_get_context_returns_empty_dict_by_default(self):
        resource = DummyEMRResource()
        self.assertEqual(resource.get_context(), {})

    def test_get_context_returns_context_when_set(self):
        resource = DummyEMRResourceWithContext()
        self.assertEqual(
            resource.get_context(), {"user": "test_user", "is_create": True}
        )
