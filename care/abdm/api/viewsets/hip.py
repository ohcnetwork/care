import uuid
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.hip import HipShareProfileSerializer
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import AbdmGateway, HealthIdGateway
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientRegistration
from config.authentication import ABDMAuthentication


class HipViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def get_linking_token(self, data):
        AbdmGateway().fetch_modes(data)
        return True

    @action(detail=False, methods=["POST"])
    def share(self, request, *args, **kwargs):
        data = request.data

        patient_data = data["profile"]["patient"]
        counter_id = (
            data["profile"]["hipCode"]
            if len(data["profile"]["hipCode"]) == 36
            else Facility.objects.first().external_id
        )

        patient_data["mobile"] = ""
        for identifier in patient_data["identifiers"]:
            if identifier["type"] == "MOBILE":
                patient_data["mobile"] = identifier["value"]

        serializer = HipShareProfileSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        if HealthIdGateway().verify_demographics(
            patient_data["healthIdNumber"],
            patient_data["name"],
            patient_data["gender"],
            patient_data["yearOfBirth"],
        ):
            patient = PatientRegistration.objects.filter(
                abha_number__abha_number=patient_data["healthIdNumber"]
            ).first()

            if not patient:
                patient = PatientRegistration.objects.create(
                    facility=Facility.objects.get(external_id=counter_id),
                    name=patient_data["name"],
                    gender={"M": 1, "F": 2}.get(patient_data["gender"], 3),
                    is_antenatal=False,
                    phone_number=patient_data["mobile"],
                    emergency_phone_number=patient_data["mobile"],
                    date_of_birth=datetime.strptime(
                        f"{patient_data['yearOfBirth']}-{patient_data['monthOfBirth']}-{patient_data['dayOfBirth']}",
                        "%Y-%m-%d",
                    ).date(),
                    blood_group="UNK",
                    nationality="India",
                    address=patient_data["address"]["line"],
                    pincode=patient_data["address"]["pincode"],
                )

                abha_number = AbhaNumber.objects.create(
                    abha_number=patient_data["healthIdNumber"],
                    health_id=patient_data["healthId"],
                    name=patient_data["name"],
                    gender=patient_data["gender"],
                    date_of_birth=str(
                        datetime.strptime(
                            f"{patient_data['yearOfBirth']}-{patient_data['monthOfBirth']}-{patient_data['dayOfBirth']}",
                            "%Y-%m-%d",
                        )
                    )[0:10],
                    address=patient_data["address"]["line"],
                    district=patient_data["address"]["district"],
                    state=patient_data["address"]["state"],
                    pincode=patient_data["address"]["pincode"],
                )

                try:
                    self.get_linking_token(
                        {
                            "healthId": patient_data["healthId"]
                            or patient_data["healthIdNumber"],
                            "name": patient_data["name"],
                            "gender": patient_data["gender"],
                            "dateOfBirth": str(
                                datetime.strptime(
                                    f"{patient_data['yearOfBirth']}-{patient_data['monthOfBirth']}-{patient_data['dayOfBirth']}",
                                    "%Y-%m-%d",
                                )
                            )[0:10],
                        }
                    )
                except Exception:
                    return Response(
                        {
                            "status": "FAILED",
                            "healthId": patient_data["healthId"]
                            or patient_data["healthIdNumber"],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                abha_number.save()
                patient.abha_number = abha_number
                patient.save()

            payload = {
                "requestId": str(uuid.uuid4()),
                "timestamp": str(
                    datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                ),
                "acknowledgement": {
                    "status": "SUCCESS",
                    "healthId": patient_data["healthId"]
                    or patient_data["healthIdNumber"],
                    "tokenNumber": "100",
                },
                "error": None,
                "resp": {
                    "requestId": data["requestId"],
                },
            }

            on_share_response = AbdmGateway().on_share(payload)
            if on_share_response.status_code == 202:
                return Response(
                    on_share_response.request.body,
                    status=status.HTTP_202_ACCEPTED,
                )

        return Response(
            {
                "status": "ACCEPTED",
                "healthId": patient_data["healthId"] or patient_data["healthIdNumber"],
            },
            status=status.HTTP_202_ACCEPTED,
        )
