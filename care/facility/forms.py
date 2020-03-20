from django.forms import ModelForm

from .models import Facility, FacilityCapacity, HospitalDoctors


class FacilityCreationForm(ModelForm):
    class Meta:
        model = Facility
        fields = ["name", "district", "address"]


class FacilityCapacityCreationForm(ModelForm):
    class Meta:
        model = FacilityCapacity
        fields = ["room_type", "total_capacity", "current_capacity"]


class DoctorsCountCreationForm(ModelForm):
    class Meta:
        model = HospitalDoctors
        fields = ["area", "count"]
