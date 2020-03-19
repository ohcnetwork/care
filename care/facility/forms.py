from django.forms import ModelForm

from .models import Facility, FacilityCapacity


class FacilityCreationForm(ModelForm):
    class Meta:
        model = Facility
        fields = ["name", "district"]


class FacilityCapacityCreationForm(ModelForm):
    class Meta:
        model = FacilityCapacity
        fields = ["room_type", "capacity"]
