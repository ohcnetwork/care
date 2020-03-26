from django.forms import ModelForm

from .models import Facility, FacilityCapacity, HospitalDoctors


class FacilityCreationForm(ModelForm):
    class Meta:
        model = Facility
        fields = ["name", "district", "address", "oxygen_capacity", "phone_number"]
        labels = {
            "name": "Enter the name of your hospital",
            "district": "Pick your District",
            "address": "Enter Hospital Address",
            "phone_number": "Enter emergency contact number of your hospital",
            "oxygen_capacity": "Enter the total oxygen capacity of your hospital (in litres)",
        }


class FacilityCapacityCreationForm(ModelForm):
    class Meta:
        model = FacilityCapacity
        fields = ["room_type", "total_capacity", "current_capacity"]
        labels = {"room_type": "Bed Type", "total_capacity": "Total Capacity", "current_capacity": "Currently Occupied"}


class DoctorsCountCreationForm(ModelForm):
    class Meta:
        model = HospitalDoctors
        fields = ["area", "count"]
        labels = {"area": "Area of specialization"}
