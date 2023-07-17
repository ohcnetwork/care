from unittest.mock import patch

from celery import Celery

from care.facility.tasks import setup_periodic_tasks


@patch("care.facility.tasks.asset_monitor.check_asset_status.delay")
def test_setup_periodic_tasks(mock_check_asset_status):
    app = Celery()
    setup_periodic_tasks(app)

    # Ensure that check_asset_status is called immediately
    mock_check_asset_status.assert_called_once()
