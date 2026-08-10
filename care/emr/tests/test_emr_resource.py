from django.test import TestCase
from care.emr.resources.base import EMRResource

class DummyEMRResource(EMRResource):
    pass

class DummyEMRResourceUpdate(EMRResource):
    _is_update = True

class EMRResourceTestCase(TestCase):
    def test_is_update_returns_false_by_default(self):
        resource = DummyEMRResource()
        self.assertFalse(resource.is_update())

    def test_is_update_returns_true_when_set(self):
        resource = DummyEMRResourceUpdate()
        self.assertTrue(resource.is_update())
