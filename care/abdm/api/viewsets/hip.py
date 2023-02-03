import uuid
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.hip import HipShareProfileSerializer
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import AbdmGateway, HealthIdGateway
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientRegistration


class HipViewSet(GenericViewSet):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def add_abha_details_to_patient(self, data, patient_obj):
        abha_object = AbhaNumber.objects.filter(
            abha_number=data["healthIdNumber"]
        ).first()
        if abha_object:
            # Flow when abha number exists in db somehow!
            pass
        else:
            # Create abha number flow
            abha_object = AbhaNumber()
            abha_object.abha_number = data["healthIdNumber"]
            # abha_object.email = data["email"]
            # abha_object.first_name = data["firstName"]
            abha_object.health_id = data["healthId"]
            # abha_object.last_name = data["lastName"]
            # abha_object.middle_name = data["middleName"]
            # abha_object.profile_photo = data["profilePhoto"]
            abha_object.save()

        patient_obj.abha_number = abha_object
        patient_obj.save()
        return True

    def demographics_verification(self, data):
        auth_init_response = HealthIdGateway().auth_init(
            {"authMethod": "DEMOGRAPHICS", "healthid": data["healthIdNumber"]}
        )
        if "txnId" in auth_init_response:
            demographics_response = HealthIdGateway().confirm_with_demographics(
                {
                    "txnId": auth_init_response["txnId"],
                    "name": data["name"],
                    "gender": data["gender"],
                    "yearOfBirth": data["yearOfBirth"],
                }
            )
            return "status" in demographics_response and demographics_response["status"]
        else:
            return False

    @action(detail=False, methods=["POST"])
    def share(self, request, *args, **kwargs):
        data = request.data

        patient_data = data["profile"]["patient"]
        counter_id = data["profile"]["hipCode"]

        patient_data["mobile"] = ""
        for identifier in patient_data["identifiers"]:
            if identifier["type"] == "MOBILE":
                patient_data["mobile"] = identifier["value"]

        serializer = HipShareProfileSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        if self.demographics_verification(patient_data):
            patient = PatientRegistration.objects.filter(
                abha_number__abha_number=patient_data["healthIdNumber"]
            )

            if not patient:
                patient = PatientRegistration.objects.create(
                    facility=Facility.objects.get(external_id=counter_id),
                    name=patient_data["name"],
                    gender=1
                    if patient_data["gender"] == "M"
                    else 2
                    if patient_data["gender"] == "F"
                    else 3,
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
                    created_by=None,
                    state=None,
                    district=None,
                    local_body=None,
                    ward=None,
                )
                self.add_abha_details_to_patient(patient_data, patient)

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
                print("on_share_header", on_share_response.request.body)
                return Response(
                    on_share_response.request.body,
                    status=status.HTTP_202_ACCEPTED,
                )

        return Response(
            {
                "status": "FAILURE",
                "healthId": patient_data["healthId"] or patient_data["healthIdNumber"],
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
