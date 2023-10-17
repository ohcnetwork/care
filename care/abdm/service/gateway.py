import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.db.models import Q

from care.abdm.models.abha_number import AbhaNumber
from care.abdm.models.base import Purpose
from care.abdm.models.consent import ConsentArtefact, ConsentRequest
from care.abdm.service.request import Request


class Gateway:
    def __init__(self):
        self.request = Request(settings.ABDM_URL + "/gateway")

    def consent_requests__init(self, consent: ConsentRequest):
        data = {
            "requestId": str(consent.external_id),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "consent": {
                "purpose": {
                    "text": Purpose(consent.purpose).label,
                    "code": Purpose(consent.purpose).value,
                },
                "patient": {"id": consent.patient_abha.health_id},
                "hiu": {
                    "id": "IN3210000017"
                },  # TODO: get the HIU ID associated with the patient's facility
                "requester": {
                    "name": f"{consent.requester.REVERSE_TYPE_MAP[consent.requester.user_type]}, {consent.requester.first_name} {consent.requester.last_name}",
                    "identifier": {
                        "type": "Care Username",
                        "value": consent.requester.username,
                        "system": settings.CURRENT_DOMAIN,
                    },
                },
                "hiTypes": consent.hi_types,
                "permission": {
                    "accessMode": consent.access_mode,
                    "dateRange": {
                        "from": consent.from_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "to": consent.to_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    },
                    "dataEraseAt": consent.expiry.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "frequency": {
                        "unit": consent.frequency_unit,
                        "value": consent.frequency_value,
                        "repeats": consent.frequency_repeats,
                    },
                },
            },
        }

        path = "/v0.5/consent-requests/init"
        return self.request.post(path, data, headers={"X-CM-ID": settings.X_CM_ID})

    def consent_requests__status(self, consent_request_id: str):
        data = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "consentRequestId": consent_request_id,
        }

        return self.request.post(
            "/v0.5/consent-requests/status", data, headers={"X-CM-ID": settings.X_CM_ID}
        )

    def consents__hiu__notify(self, consent_id: str, request_id: str):
        data = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "acknowledgement": {
                "consentId": consent_id,
                "status": "OK",
            },
            "resp": {"requestId": request_id},
        }

        return self.request.post(
            "/v0.5/consents/hiu/notify", data, headers={"X-CM-ID": settings.X_CM_ID}
        )

    def consents__fetch(self, consent_artefact_id: str):
        data = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "consentId": consent_artefact_id,
        }

        return self.request.post(
            "/v0.5/consents/fetch", data, headers={"X-CM-ID": settings.X_CM_ID}
        )

    def health_information__cm__request(self, artefact: ConsentArtefact):
        request_id = str(uuid.uuid4())
        artefact.consent_id = request_id
        artefact.save()

        data = {
            "requestId": request_id,
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "hiRequest": {
                "consent": {"id": str(artefact.artefact_id)},
                # TODO: get the server url from the env
                "dataPushUrl": "https://work.khavinshankar.dev"
                + "/v0.5/health-information/transfer",
                "keyMaterial": {
                    "cryptoAlg": artefact.key_material_algorithm,
                    "curve": artefact.key_material_curve,
                    "dhPublicKey": {
                        "expiry": artefact.expiry.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "parameters": f"{artefact.key_material_curve}/{artefact.key_material_algorithm}",
                        "keyValue": artefact.key_material_public_key,
                    },
                    "nonce": artefact.key_material_nonce,
                },
            },
        }

        return self.request.post(
            "/v0.5/health-information/cm/request",
            data,
            headers={"X-CM-ID": settings.X_CM_ID},
        )

    def get_hf_id_by_health_id(self, health_id):
        return (
            AbhaNumber.objects.filter(Q(abha_number=health_id) | Q(health_id=health_id))
            .first()
            .patientregistration.facility.healthfacility.hf_id
        )

    def health_information__notify(self, artefact: ConsentArtefact):
        data = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "notification": {
                "consentId": str(artefact.artefact_id),
                "transactionId": str(artefact.transaction_id),
                "doneAt": datetime.now(tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),
                "notifier": {
                    "type": "HIU",
                    "id": self.get_hf_id_by_health_id(artefact.patient_abha.health_id),
                },
            },
            "statusNotification": {
                "sessionStatus": "TRANSFERRED",
                "hipId": artefact.hip,
            },
        }

        return self.request.post(
            "/v0.5/health-information/notify",
            data,
            headers={"X-CM-ID": settings.X_CM_ID},
        )

    def patients__find(self, abha_number: AbhaNumber):
        data = {
            "requestId": str(uuid.uuid4()),
            "timestamp": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "query": {
                "patient": {"id": abha_number.health_id},
                "requester": {
                    "type": "HIU",
                    "id": abha_number.patientregistration.facility.healthfacility.hf_id,
                },
            },
        }

        return self.request.post(
            "/v0.5/patients/find", data, headers={"X-CM-ID": settings.X_CM_ID}
        )
