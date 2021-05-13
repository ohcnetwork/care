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
    pulse_rate = serializers.IntegerField(allow_null=True)
    blood_pressure_systolic = serializers.IntegerField(allow_null=True)
    blood_pressure_diastolic = serializers.IntegerField(allow_null=True)
    respiration_rate = serializers.IntegerField(allow_null=True)
    oxygen_saturation = serializers.IntegerField(allow_null=True)


# Validator serializer for on_examination_vitals
class OnExaminationVitalsSerializer(serializers.Serializer):
    pulse_rate = serializers.IntegerField(allow_null=True)
    blood_pressure_systolic = serializers.IntegerField(allow_null=True)
    blood_pressure_diastolic = serializers.IntegerField(allow_null=True)
    respiration_rate = serializers.IntegerField(allow_null=True)
    temperature = serializers.FloatField(allow_null=True)
    oxygen_saturation = serializers.IntegerField(allow_null=True)


# Validator serializer for each object of steroids_drugs,
# antibiotics_drugs and antifungals_drugs fields
class DrugInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    duration = serializers.IntegerField()


# validator serializer for anticoagulants_drugs field
class AnticoagulantDrugInfoSerializer(serializers.Serializer):
    mode_of_transmission = ChoiceField(choices=ModeOfTransmissionChoices)
    name = serializers.CharField()
    duration = serializers.IntegerField()


# validator serializer for systemic_examination field
class SystemicExaminationSerializer(serializers.Serializer):
    respiratory = serializers.JSONField()
    cvs = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)
    cns = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)
    git = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)

    def validate_respiratory(self, respiratory):
        if (
            len(respiratory) != 3 or
            not RespiratorySerializer(data=respiratory).is_valid()
        ):
            raise serializers.ValidationError(
                "Respiratory part of systemic examination is invalid"
            )


# validator serializer for respiratory attribute of systemic_examination field
class RespiratorySerializer(serializers.Serializer):
    wob = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)
    rhonchi = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)
    crepitation = serializers.CharField(style={'base_template': 'textarea.html'}, allow_null=True, allow_blank=True)


class PostCovidDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostCovidData
        read_only_fields = TIMESTAMP_FIELDS
        exclude = TIMESTAMP_FIELDS + ("id",)
        required_fields = [
            "post_covid_time",
            "date_of_test_positive",
            "date_of_test_negative",
            "treatment_facility",
            "treatment_duration",
            "icu_admission",
            "oxygen_requirement",
            "probable_diagnosis"
        ]
        extra_kwargs = {i: {'required': True} for i in required_fields}

    def validate_vitals_at_admission(self, vitals_at_admission):
        if vitals_at_admission is not None:
            v = VitalsAtAdmissionSerializer(data=vitals_at_admission)
            if(
                len(vitals_at_admission) != 5 or
                not v.is_valid()
            ):
                raise serializers.ValidationError("All vitals at admission were not provided.")

        return vitals_at_admission

    def validate_on_examination_vitals(self, on_examination_vitals):
        if on_examination_vitals is not None:
            if(
                len(on_examination_vitals) != 6 or
                not OnExaminationVitalsSerializer(data=on_examination_vitals).is_valid()
            ):
                raise serializers.ValidationError("All examination vitals were not provided.")

        return on_examination_vitals

    def validateDrugs(self, drugs, drugName):
        if drugs is not None:
            for drug_info in drugs:
                if(
                    len(drug_info) != 2 or
                    not DrugInfoSerializer(data=drug_info).is_valid()
                ):
                    raise serializers.ValidationError("Invalid drug information of {} drugs".format(drugName))

    def validate_steroids_drugs(self, steroids_drugs):
        self.validateDrugs(steroids_drugs, "steroid")
        return steroids_drugs

    def validate_antibiotics_drugs(self, antibiotics_drugs):
        self.validateDrugs(antibiotics_drugs, "antibiotic")
        return antibiotics_drugs

    def validate_antifungals_drugs(self, antifungals_drugs):
        self.validateDrugs(antifungals_drugs, "antifungal")
        return antifungals_drugs

    def validate_anticoagulants_drugs(self, anticoagulants_drugs):
        if anticoagulants_drugs is not None:
            for drug_info in anticoagulants_drugs:
                if(
                    len(drug_info) != 3 or
                    not AnticoagulantDrugInfoSerializer(data=drug_info).is_valid()
                ):
                    raise serializers.ValidationError(
                        "Invalid drug information of anticoagulants drugs"
                    )

        return anticoagulants_drugs

    def validate_systemic_examination(self, systemic_examination):
        if systemic_examination is not None:
            if(
                len(systemic_examination) != 4 or
                not SystemicExaminationSerializer(data=systemic_examination).is_valid()
            ):
                raise serializers.ValidationError("Invalid systemic examination information")

        return systemic_examination

    def validate(self, data):
        if data['date_of_test_positive'] > data['date_of_test_negative']:
            raise serializers.ValidationError(
                "Date of test positive cannot be after date of test negative"
            )

        return super().validate(data)
