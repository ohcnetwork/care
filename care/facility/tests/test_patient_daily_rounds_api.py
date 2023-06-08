from care.utils.tests.test_base import TestBase
from care.facility.models.daily_round import DailyRound
from rest_framework import status

class TestDailyRoundApi(TestBase):

    def get_url(self, external_consultation_id=None):
        return F"/api/v1/consultation/{external_consultation_id}/daily_rounds/analyse/"

    def test_external_consultation_does_not_exists_returns_404(self):
        sample_uuid = "e4a3d84a-d678-4992-9287-114f029046d8"
        response = self.client.get(self.get_url(sample_uuid))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    