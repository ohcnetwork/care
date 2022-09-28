from celery.decorators import periodic_task
from celery.schedules import crontab

from care.facility.models import Asset
from care.utils.assetintegration.hl7monitor import HL7MonitorAsset
from care.utils.assetintegration.onvif import OnvifAsset


@periodic_task(run_every=crontab(minute="*/10"))
def sync_asset_status():
    assets = Asset.objects.all()
    for asset in assets:
        if asset.asset_class == OnvifAsset._name:
            asset_integration = OnvifAsset()
            asset_integration.handle_action(
                {"type": OnvifAsset.OnvifActions.GET_CAMERA_STATUS, "data": ""}
            )
            # manipulate asset here

        elif asset.asset_class == HL7MonitorAsset._name:
            asset_integration = HL7MonitorAsset()
            asset_integration.handle_action(
                {
                    "type": HL7MonitorAsset.HL7MonitorActions.GET_VITALS,
                    "data": {
                        "device_id": "",
                    },
                }
            )
            # manipulate asset here

        asset.save()
