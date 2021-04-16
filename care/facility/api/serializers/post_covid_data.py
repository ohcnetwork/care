# to be done
# mark required fields according to pdf - done
# mark null and blank in model according to pdf - done
# format model and serializer - done
# change validation error messages of all

# if oxygen_requirement is NO then oxygen_requirement_detail should be null or empty string? If it can be null, then this cannot be a mandatory field. If mandatory, mark blank=True in model
# for patients field, what should be value of on_delete, means what should be done if patient is deleted- protect
# are there any read only fields?

import enum
from rest_framework import serializers
from config.serializers import ChoiceField
from care.facility.api.serializers import TIMESTAMP_FIELDS
from care.facility.models.post_covid_data import PostCovidData


# choices for mode_of_transmission attribute of anticoagulants_drugs field
class ModeOfTransmission(enum.Enum):
    IV = "IV"
    ORAL = "Oral"


ModeOfTransmissionChoices = [(e.value, e.name) for e in ModeOfTransmission]


# Validator serializer for vitals_at_admission
class VitalsAtAdmissionSerializer(serializers.Serializer):
    pr = serializers.IntegerField()
    bp_systolic = serializers.IntegerField()
    bp_diastolic = serializers.IntegerField()
    rr = serializers.IntegerField()
    spo2 = serializers.IntegerField()

# Validator serializer for on_examination_vitals


class OnExaminationVitalsSerializer(serializers.Serializer):
    pr = serializers.IntegerField()
    bp_systolic = serializers.IntegerField()
    bp_distolic = serializers.IntegerField()
    rr = serializers.IntegerField()
    temperature = serializers.FloatField()
    spo2 = serializers.IntegerField()

# Validator serializer for each object of steroids_drugs,
# antibiotics_drugs and antifungals_drugs fields


class DrugInfoSerializer(serializers.Serializer):
    drug = serializers.CharField()
    duration = serializers.IntegerField()

# validator serializer for anticoagulants_drugs field


class AnticoagulantDrugInfoSerializer(serializers.Serializer):
    mode_of_transmission = ChoiceField(choices=ModeOfTransmissionChoices)
    drug = serializers.CharField()
    duration = serializers.IntegerField()

# validator serializer for systemic_examination field


class SystemicExaminationSerializer(serializers.Serializer):
    respiratory = serializers.JSONField()
    # cvs = serializers.TextField()
    cvs = serializers.CharField(style={'base_template': 'textarea.html'})
    # cns = serializers.TextField()
    cns = serializers.CharField(style={'base_template': 'textarea.html'})
    # git = serializers.TextField()
    git = serializers.CharField(style={'base_template': 'textarea.html'})

    def validate_respiratory(self, respiratory):
        if len(respiratory) != 3 or not RespiratorySerializer(data=respiratory).is_valid():
            raise serializers.ValidationError(
                "Respiratory part of systemic examination is invalid"
            )

# validator serializer for respiratory attribute of systemic_examination field


class RespiratorySerializer(serializers.Serializer):
    # wob = serializers.TextField()
    # rhonchi = serializers.TextField()
    # crepitation = serializers.TextField()
    wob = serializers.CharField(style={'base_template': 'textarea.html'})
    rhonchi = serializers.CharField(style={'base_template': 'textarea.html'})
    crepitation = serializers.CharField(style={'base_template': 'textarea.html'})


class PostCovidDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = PostCovidData
        # fields = "__all__"
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
        required_fields = [
            "post_covid_time",
            "date_of_test_positive",
            "date_of_test_negative",
            "treatment_facility",
            "treatment_duration",
            "covid_category",
            "icu_admission",
            "oxygen_requirement",
            "at_present_symptoms",
            "probable_diagnosis"
        ]
        extra_kwargs = {i: {'required': True} for i in required_fields}

    def validate_vitals_at_admission(self, vitals_at_admission):
        if vitals_at_admission == None:
            return vitals_at_admission

        v = VitalsAtAdmissionSerializer(data=vitals_at_admission)

        if(
            len(vitals_at_admission) != 4 or
            not v.is_valid()
        ):
            v.is_valid(raise_exception=True)
            # raise serializers.ValidationError("All vitals were not provided.")

        return vitals_at_admission

    def validate_on_examination_vitals(self, on_examination_vitals):
        if on_examination_vitals == None:
            return on_examination_vitals

        if(
            len(on_examination_vitals) != 5 or
            not OnExaminationVitalsSerializer(data=on_examination_vitals).is_valid()
        ):
            raise serializers.ValidationError("All vitals were not provided.")

        return on_examination_vitals

    def validate_steroids_drugs(self, steroids_drugs):
        if steroids_drugs == None:
            return steroids_drugs

        for drug_info in steroids_drugs:
            if(
                len(steroids_drugs) != 2 or
                not DrugInfoSerializer(data=drug_info).is_valid()
            ):
                raise serializers.ValidationError("Invalid drug information")

        return steroids_drugs

    def validate_antivirals_drugs(self, antivirals_drugs):
        if antivirals_drugs == None:
            return antivirals_drugs

        for drug_info in antivirals_drugs:
            if(
                len(drug_info) != 2 or
                not DrugInfoSerializer(data=drug_info).is_valid()
            ):
                raise serializers.ValidationError("Invalid drug information")

    def validate_anticoagulants_drugs(self, anticoagulants_drugs):
        if anticoagulants_drugs == None:
            return anticoagulants_drugs

        for drug_info in anticoagulants_drugs:
            if(
                len(drug_info) != 3 or
                not AnticoagulantDrugInfoSerializer(data=drug_info).is_valid()
            ):
                raise serializers.ValidationError("Invalid drug information")

        return anticoagulants_drugs

    def validate_antibiotics_drugs(self, antibiotics_drugs):
        if antibiotics_drugs == None:
            return antibiotics_drugs

        for drug_info in antibiotics_drugs:
            if(
                len(antibiotics_drugs) != 2 or
                not DrugInfoSerializer(data=drug_info).is_valid()
            ):
                raise serializers.ValidationError("Invalid drug information")

        return antibiotics_drugs

    def validate_antifungals_drugs(self, antifungals_drugs):
        if antifungals_drugs == None:
            return antifungals_drugs

        for drug_info in antifungals_drugs:
            if(
                len(antifungals_drugs) != 2 or
                not DrugInfoSerializer(data=drug_info).is_valid()
            ):
                raise serializers.ValidationError("Invalid drug information")

        return antifungals_drugs

    def validate(self, data):
        if data['date_of_test_positive'] > data['date_of_test_negative']:
            raise serializers.ValidationError("Date of test positive is invalid")

        return super().validate(data)

    def validate_systemic_examination(self, systemic_examination):
        if systemic_examination == None:
            return systemic_examination

        if(
            len(systemic_examination) != 4 or
            not SystemicExaminationSerializer(data=systemic_examination).is_valid()
        ):
            raise serializers.ValidationError("Invalid systemic examination information")

    def create(self, *args, **kwargs):
        print("args : ", args, kwargs)
        return super().create(*args, **kwargs)
