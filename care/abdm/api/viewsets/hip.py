import datetime

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.hip import HipShareProfileSerializer
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import HealthIdGateway
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientRegistration


class HipViewSet(GenericViewSet):
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
    def share_profile(self, request, *args, **kwargs):
        data = request.data
        patient_data = data["profile"]["patient"]
        # hip_id = self.request.GET.get("hip_id")
        counter_id = self.request.GET.get("counter_id")  # facility_id

        patient_data["mobile"] = ""
        for identifier in patient_data["identifiers"]:
            if identifier["type"] == "MOBILE":
                patient_data["mobile"] = identifier["value"]

        serializer = HipShareProfileSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        # create a patient or search for existing patient with this abha number
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
                date_of_birth=datetime.datetime.strptime(
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

        # verify details using demographics method (name, gender and yearOfBirth)
        if self.demographics_verification(patient_data):
            self.add_abha_details_to_patient(patient_data, patient)
            return Response(
                {
                    "requestId": data["requestId"],
                    "timestamp": str(datetime.datetime.now()),
                    "acknowledgement": {
                        "status": "SUCCESS",
                        "healthId": patient_data["healthId"],
                        "healthIdNumber": patient_data["healthIdNumber"],
                        "tokenNumber": "01",  # this is for out patients
                    },
                },
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {
                    "requestId": data["requestId"],
                    "timestamp": str(datetime.datetime.now()),
                    "acknowledgement": {
                        "status": "FAILURE",
                    },
                    "error": {
                        "code": 1000,
                        "message": "Demographics verification failed",
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
