from django.forms import ModelForm

from .models import Facility, FacilityCapacity, HospitalDoctors


class FacilityCreationForm(ModelForm):
    class Meta:
        model = Facility
        fields = ["name", "district"]


class FacilityCapacityCreationForm(ModelForm):
    class Meta:
        model = FacilityCapacity
        fields = ["room_type", "capacity"]


class DoctorsCountCreationForm(ModelForm):
    class Meta:
        model = HospitalDoctors
        fields = ["area", "count"]
