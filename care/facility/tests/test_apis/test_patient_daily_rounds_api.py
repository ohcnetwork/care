from care.utils.tests.test_base import TestBase


class TestPatientDailyRounds(TestBase):
    def get_base_url(self):
        return f"/api/v1/consultation/{self.consultation.id}/daily_rounds"

    def get_list_representation(self, obj) -> dict:
        pass

    def get_detail_representation(self, obj=None) -> dict:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        super(TestPatientDailyRounds, cls).setUpClass()
