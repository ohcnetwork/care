from care.emr.resources.activity_definition.spec import BaseActivityDefinitionSpec
from care.emr.resources.healthcare_service.spec import BaseHealthcareServiceSpec
from care.emr.resources.observation_definition.spec import BaseObservationDefinitionSpec
from care.emr.resources.specimen_definition.spec import BaseSpecimenDefinitionSpec

from . import create_charge_item_definition, create_object, create_resource_category
from .facilities import create_location


def setup_clinical(ctx):
    """Create lab definitions and clinical objects for the primary facility."""
    create_lab_definition_objects(ctx.fake, ctx.facility, ctx.super_user)
    ctx.log("Created lab objects for facility")


def create_specimen_definition(facility, user=None, slug=None, **kwargs):
    """Create a SpecimenDefinition for a facility."""
    extra = {}
    if slug:
        extra["slug"] = slug
    return create_object(
        BaseSpecimenDefinitionSpec(**kwargs),
        facility,
        user,
        **extra,
    )


def create_observation_definition(facility, user=None, **kwargs):
    """Create an ObservationDefinition for a facility."""
    spec_keys = {
        "title", "status", "description", "category", "code",
        "permitted_data_type", "qualified_ranges", "component",
        "method", "permitted_unit",
    }
    spec_kwargs = {k: v for k, v in kwargs.items() if k in spec_keys}
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in spec_keys}
    return create_object(
        BaseObservationDefinitionSpec(**spec_kwargs),
        facility,
        user,
        **extra_kwargs,
    )


def create_activity_definition(facility, user=None, **kwargs):
    """Create an ActivityDefinition for a facility."""
    spec_keys = {
        "id", "title", "status", "description", "usage", "classification",
        "category", "kind", "code", "diagnostic_report_codes", "derived_from_uri",
    }
    spec_kwargs = {k: v for k, v in kwargs.items() if k in spec_keys}
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in spec_keys}
    return create_object(
        BaseActivityDefinitionSpec(**spec_kwargs),
        facility,
        user,
        **extra_kwargs,
    )


def create_healthcare_service(facility, user=None, **kwargs):
    """Create a HealthcareService for a facility."""
    spec_keys = {"internal_type", "name", "styling_metadata", "extra_details"}
    spec_kwargs = {k: v for k, v in kwargs.items() if k in spec_keys}
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in spec_keys}
    return create_object(
        BaseHealthcareServiceSpec(**spec_kwargs),
        facility,
        user,
        **extra_kwargs,
    )


def create_lab_definition_objects(fake, facility, user=None):  # noqa: PLR0915
    bio_chemistry_lab_location = create_location(
        fake,
        user or facility.created_by,
        facility,
        [facility.default_internal_organization],
        mode="kind",
        form="ro",
        name="Bio-Chemistry Lab",
    )

    code_ucum_ml = {
        "code": "mL",
        "system": "http://unitsofmeasure.org",
        "display": "milliliter",
    }
    code_ucum_h = {
        "code": "h",
        "system": "http://unitsofmeasure.org",
        "display": "hours",
    }
    code_ucum_g_dl = {
        "code": "g/dL",
        "system": "http://unitsofmeasure.org",
        "display": "gram per deciliter",
    }
    code_ucum_d = {
        "code": "d",
        "system": "http://unitsofmeasure.org",
        "display": "days",
    }
    code_ucum_percent = {
        "code": "%",
        "system": "http://unitsofmeasure.org",
        "display": "percent",
    }
    code_ucum_million_per_ul = {
        "code": "10*6/uL",
        "system": "http://unitsofmeasure.org",
        "display": "million per microliter",
    }
    code_ucum_thousands_per_ul = {
        "code": "10*3/uL",
        "system": "http://unitsofmeasure.org",
        "display": "Thousands Per MicroLiter",
    }
    code_hl7_bldv = {
        "code": "BLDV",
        "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
        "display": "Blood venous",
    }
    code_hl7_ur = {
        "code": "UR",
        "system": "http://terminology.hl7.org/CodeSystem/v2-0487",
        "display": "Urine",
    }
    code_hl7_grey_cap = {
        "code": "grey",
        "system": "http://terminology.hl7.org/CodeSystem/container-cap",
        "display": "grey cap",
    }
    code_hl7_lavender_cap = {
        "code": "lavender",
        "system": "http://terminology.hl7.org/CodeSystem/container-cap",
        "display": "lavender cap",
    }
    code_hl7_yellow_cap = {
        "code": "yellow",
        "system": "http://terminology.hl7.org/CodeSystem/container-cap",
        "display": "yellow cap",
    }
    code_hl7_dark_yellow_cap = {
        "code": "dark-yellow",
        "system": "http://terminology.hl7.org/CodeSystem/container-cap",
        "display": "dark yellow cap",
    }
    code_snomed_after_fasting = {
        "code": "726054005",
        "system": "http://snomed.info/sct",
        "display": "After fasting",
    }
    code_snomed_same_day_before_procedure = {
        "code": "47531000087108",
        "system": "http://snomed.info/sct",
        "display": "Same day but before procedure",
    }
    code_snomed_puncture = {
        "code": "129300006",
        "system": "http://snomed.info/sct",
        "display": "Puncture - action",
    }
    code_snomed_urine_clean_catch = {
        "code": "73416001",
        "system": "http://snomed.info/sct",
        "display": "Urine specimen collection, clean catch",
    }
    code_snomed_automated_count = {
        "code": "702659008",
        "system": "http://snomed.info/sct",
        "display": "Automated count",
    }
    code_snomed_urine_dipstick = {
        "code": "167226008",
        "system": "http://snomed.info/sct",
        "display": "Urine dipstick test",
    }
    code_snomed_cbc = {
        "code": "26604007",
        "system": "http://snomed.info/sct",
        "display": "Complete blood count",
    }
    code_snomed_fasting_glucose = {
        "code": "271062006",
        "system": "http://snomed.info/sct",
        "display": "Fasting blood glucose measurement",
    }
    code_loinc_fasting_glucose = {
        "code": "1558-6",
        "system": "http://loinc.org",
        "display": "Fasting glucose [Mass/volume] in Serum or Plasma",
    }
    code_loinc_cbc_panel = {
        "code": "58410-2",
        "system": "http://loinc.org",
        "display": "CBC panel - Blood by Automated count",
    }
    code_loinc_hemoglobin = {
        "code": "LP32067-8",
        "system": "http://loinc.org",
        "display": "Hemoglobin",
    }
    code_loinc_hematocrit = {
        "code": "LP15101-6",
        "system": "http://loinc.org",
        "display": "Hematocrit",
    }
    code_loinc_erythrocytes = {
        "code": "LA12896-9",
        "system": "http://loinc.org",
        "display": "Erythrocytes",
    }
    code_loinc_platelets = {
        "code": "LP7631-7",
        "system": "http://loinc.org",
        "display": "Platelets",
    }
    code_snomed_lipid_panel = {
        "code": "16254007",
        "system": "http://snomed.info/sct",
        "display": "Lipid panel",
    }
    code_snomed_urine = {
        "code": "442564008",
        "system": "http://snomed.info/sct",
        "display": "Evaluation of urine specimen",
    }
    code_loinc_lipid_panel = {
        "code": "LP97557-0",
        "system": "http://loinc.org",
        "display": "Lipid panel with direct LDL",
    }
    code_loinc_urine = {
        "code": "LP7681-2",
        "system": "http://loinc.org",
        "display": "Urine",
    }
    code_loinc_fasting_glucose_serum = {
        "code": "1558-6",
        "system": "http://loinc.org",
        "display": "Fasting glucose [Mass/volume] in Serum or Plasma",
    }

    blood_glucose_specimen_definition = create_object(
        BaseSpecimenDefinitionSpec(
            title="Blood Glucose Test Specimen",
            status="active",
            description="A venous blood specimen collected for the quantitative measurement of glucose concentration in blood. Used in diagnosis and monitoring of diabetes mellitus and glucose metabolism disorders.",
            type_collected=code_hl7_bldv,
            patient_preparation=[code_snomed_after_fasting],
            collection=code_snomed_puncture,
            type_tested={
                "container": {
                    "cap": code_hl7_grey_cap,
                    "capacity": {"unit": code_ucum_ml, "value": 5.0},
                    "description": "Grey-top collection tube containing sodium fluoride/potassium oxalate.",
                    "preparation": "Label tube immediately after collection. Invert gently 8-10 times to mix anticoagulant. Transport to lab under cold conditions (2-8°C) if processing is delayed.",
                    "minimum_volume": {
                        "quantity": {"unit": code_ucum_ml, "value": 2.0}
                    },
                },
                "is_derived": False,
                "preference": "preferred",
                "single_use": False,
                "requirement": "Refrigerated (2-8°C). Specimen must be centrifuged and plasma separated within 2 hours of collection if not using fluoride tube. For accurate glucose measurement, immediate processing or use of glycolysis inhibitor tubes (e.g., sodium fluoride/potassium oxalate) is recommended.",
                "retention_time": {"unit": code_ucum_h, "value": 24},
            },
        ),
        facility,
        user,
        slug="blood-glucose-specimen",
    )
    cbc_specimen_definition = create_object(
        BaseSpecimenDefinitionSpec(
            title="CBC Blood Specimen",
            status="active",
            description="Whole blood specimen collected via venipuncture for performing a Complete Blood Count (CBC) test.",
            type_collected=code_hl7_bldv,
            patient_preparation=[],
            collection=code_snomed_puncture,
            type_tested={
                "container": {
                    "cap": code_hl7_lavender_cap,
                    "capacity": {"unit": code_ucum_ml, "value": 10.0},
                    "description": "Purple top EDTA tube",
                    "preparation": "Invert gently 8-10 times immediately after collection to mix with anticoagulant.",
                    "minimum_volume": {
                        "quantity": {"unit": code_ucum_ml, "value": 3.0}
                    },
                },
                "is_derived": True,
                "preference": "preferred",
                "single_use": True,
                "requirement": "Collected in EDTA tube to prevent clotting.\nShould be processed within 6 hours of collection.",
                "retention_time": {"unit": code_ucum_h, "value": 6},
            },
        ),
        facility,
        user,
        slug="cbc-blood",
    )
    lipid_panel_specimen_definition = create_object(
        BaseSpecimenDefinitionSpec(
            title="Lipid Panel Blood Specimen",
            status="active",
            description="Venous blood specimen collected to evaluate cholesterol levels including total cholesterol, HDL, LDL, and triglycerides.",
            type_collected=code_hl7_bldv,
            patient_preparation=[code_snomed_after_fasting],
            collection=code_snomed_puncture,
            type_tested={
                "container": {
                    "cap": code_hl7_dark_yellow_cap,
                    "capacity": {"unit": code_ucum_ml, "value": 5.0},
                    "description": "Serum separator tube (SST, Gold-top)",
                    "preparation": "Invert tube gently 5-6 times. Let stand upright for clotting. Centrifuge within 1 hour of collection.",
                    "minimum_volume": {
                        "quantity": {"unit": code_ucum_ml, "value": 2.0}
                    },
                },
                "is_derived": False,
                "preference": "preferred",
                "single_use": True,
                "requirement": "Refrigerated (2-8°C). Allow blood to clot at room temperature for 30 minutes. Centrifuge and separate serum promptly.",
                "retention_time": {"unit": code_ucum_d, "value": 7},
            },
        ),
        facility,
        user,
        slug="lipid-panel-specimen",
    )
    urinalysis_specimen_definition = create_object(
        BaseSpecimenDefinitionSpec(
            title="Urinalysis Specimen",
            status="active",
            description="Midstream clean-catch urine specimen collected for analysis of physical, chemical, and microscopic properties.",
            type_collected=code_hl7_ur,
            patient_preparation=[code_snomed_same_day_before_procedure],
            collection=code_snomed_urine_clean_catch,
            type_tested={
                "container": {
                    "cap": code_hl7_yellow_cap,
                    "capacity": {"unit": code_ucum_ml, "value": 100.0},
                    "description": "Sterile urine collection container with screw cap.",
                    "preparation": "Label container. Ensure tight seal to avoid contamination or leakage.",
                    "minimum_volume": {
                        "quantity": {"unit": code_ucum_ml, "value": 30.0}
                    },
                },
                "is_derived": False,
                "preference": "preferred",
                "single_use": False,
                "requirement": "Up to 24 hours refrigerated. Deliver to lab within 2 hours of collection. If delayed, refrigerate immediately.",
                "retention_time": {"unit": code_ucum_h, "value": 2},
            },
        ),
        facility,
        user,
        slug="urinalysis-specimen",
    )

    fasting_blood_glucose_observation_definition = create_object(
        BaseObservationDefinitionSpec(
            title="Fasting Blood Glucose",
            status="active",
            description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
            category="laboratory",
            code=code_loinc_fasting_glucose,
            permitted_data_type="quantity",
            qualified_ranges=[
                {
                    "conditions": [],
                    "ranges": [
                        {"interpretation": {"display": "Low"}, "max": 70},
                        {
                            "interpretation": {"display": "Normal"},
                            "min": 70,
                            "max": 99,
                        },
                        {"interpretation": {"display": "High"}, "min": 100},
                    ],
                }
            ],
        ),
        facility,
        user,
        slug="fasting_blood_glucose",
    )
    cbc_observation_definition = create_object(
        BaseObservationDefinitionSpec(
            title="Complete Blood Count",
            status="active",
            description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
            category="laboratory",
            code=code_loinc_cbc_panel,
            permitted_data_type="quantity",
            component=[
                {
                    "code": code_loinc_hemoglobin,
                    "permitted_unit": code_ucum_g_dl,
                    "permitted_data_type": "quantity",
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 12},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 12,
                                    "max": 16,
                                },
                                {"interpretation": {"display": "High"}, "min": 16},
                            ],
                        },
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 14},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 14,
                                    "max": 18,
                                },
                                {"interpretation": {"display": "High"}, "min": 18},
                            ],
                        },
                    ],
                },
                {
                    "code": code_loinc_hematocrit,
                    "permitted_unit": code_ucum_percent,
                    "permitted_data_type": "quantity",
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 36},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 36,
                                    "max": 48,
                                },
                                {"interpretation": {"display": "High"}, "min": 48},
                            ],
                        },
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 40},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 40,
                                    "max": 52,
                                },
                                {"interpretation": {"display": "High"}, "min": 52},
                            ],
                        },
                    ],
                },
                {
                    "code": code_loinc_erythrocytes,
                    "permitted_unit": code_ucum_million_per_ul,
                    "permitted_data_type": "quantity",
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 4.0},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 4.0,
                                    "max": 6.0,
                                },
                                {"interpretation": {"display": "High"}, "min": 6.0},
                            ],
                        }
                    ],
                },
                {
                    "code": code_loinc_platelets,
                    "permitted_unit": code_ucum_thousands_per_ul,
                    "permitted_data_type": "quantity",
                    "qualified_ranges": [
                        {
                            "conditions": [],
                            "ranges": [
                                {"interpretation": {"display": "Low"}, "max": 150},
                                {
                                    "interpretation": {"display": "Normal"},
                                    "min": 150,
                                    "max": 450,
                                },
                                {"interpretation": {"display": "High"}, "min": 450},
                            ],
                        }
                    ],
                },
            ],
            method=code_snomed_automated_count,
            permitted_unit=code_ucum_g_dl,
            qualified_ranges=[],
        ),
        facility,
        user,
        slug="complete-blood-count",
    )

    lipid_panel_observation_definition = create_object(
        BaseObservationDefinitionSpec(
            title="Lipid Panel Observation",
            status="active",
            description="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
            category="laboratory",
            code=code_loinc_lipid_panel,
            permitted_data_type="quantity",
            qualified_ranges=[
                {
                    "conditions": [],
                    "ranges": [
                        {"interpretation": {"display": "Desirable"}, "max": 200},
                        {
                            "interpretation": {"display": "Borderline High"},
                            "min": 200,
                            "max": 239,
                        },
                        {"interpretation": {"display": "High"}, "min": 239},
                    ],
                }
            ],
        ),
        facility,
        user,
        slug="lipid-panel-observation",
    )

    urinalysis_observation_definition = create_object(
        BaseObservationDefinitionSpec(
            title="Urinalysis Observation",
            status="active",
            description="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
            category="laboratory",
            code=code_loinc_urine,
            permitted_data_type="choice",
            method=code_snomed_urine_dipstick,
            qualified_ranges=[],
        ),
        facility,
        user,
        slug="urinalysis-observation",
    )

    default_price_components = [
        {
            "code": {
                "code": "oldage",
                "system": "http://ohc.network/codes/monetary/discount",
                "display": "Old Age Discount",
            },
            "factor": 10.0,
            "monetary_component_type": "discount",
        },
        {
            "code": {
                "code": "igst",
                "system": "http://ohc.network/codes/monetary/tax",
                "display": "IGST",
            },
            "factor": 6.0,
            "monetary_component_type": "tax",
        },
        {
            "code": {
                "code": "gst",
                "system": "http://ohc.network/codes/monetary/tax",
                "display": "GST",
            },
            "factor": 6.0,
            "monetary_component_type": "tax",
        },
    ]

    fasting_blood_glucose_charge_definition = create_charge_item_definition(
        facility,
        title="Fasting Blood Glucose Test",
        slug="fasting-glucose-test",
        description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
        purpose="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
        price_components=[
            {"amount": 600.0, "monetary_component_type": "base"},
            *default_price_components,
        ],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="charge_item_definition"
        ),
    )
    cbc_charge_definition = create_charge_item_definition(
        facility,
        title="Complete Blood Count (CBC) Test",
        slug="complete-blood-count",
        description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
        purpose="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets. This test is performed on whole blood using an automated hematology analyzer.",
        price_components=[
            {"amount": 450.0, "monetary_component_type": "base"},
            {
                "code": {
                    "code": "child",
                    "system": "http://ohc.network/codes/monetary/discount",
                    "display": "Child Discount",
                },
                "factor": 5.0,
                "monetary_component_type": "discount",
            },
            *default_price_components,
        ],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="charge_item_definition"
        ),
    )

    lipid_panel_charge_definition = create_charge_item_definition(
        facility,
        title="Lipid Panel Test",
        slug="lipid-panel-test",
        derived_from_uri="urn:chargeitem:lipid-panel",
        description="Comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
        purpose="Billing for lipid panel diagnostic service.",
        price_components=[
            {"amount": 400.0, "monetary_component_type": "base"},
            *default_price_components,
        ],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="charge_item_definition"
        ),
    )

    urinalysis_charge_definition = create_charge_item_definition(
        facility,
        title="Urinalysis Test",
        slug="urinalysis-test",
        derived_from_uri="urn:chargeitem:urinalysis",
        description="Diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
        purpose="Billing for urinalysis diagnostic service.",
        price_components=[
            {"amount": 500.0, "monetary_component_type": "base"},
            {"amount": 15.55, "monetary_component_type": "discount"},
            {
                "code": {
                    "code": "cgst",
                    "system": "http://ohc.network/codes/monetary/tax",
                    "display": "CGST",
                },
                "factor": 3.0,
                "monetary_component_type": "tax",
            },
            *default_price_components,
        ],
        version=1,
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="charge_item_definition"
        ),
    )

    create_object(
        BaseHealthcareServiceSpec(
            internal_type="lab",
            name="Pathology Lab",
            styling_metadata={"careIcon": "microscope"},
            extra_details="",
        ),
        facility,
        user,
        locations=[bio_chemistry_lab_location.id],
    )

    create_object(
        BaseActivityDefinitionSpec(
            title="Fasting Blood Glucose",
            status="active",
            description="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
            usage="Measures the concentration of glucose in plasma after 8-12 hours of fasting to screen for or monitor diabetes mellitus.",
            classification="laboratory",
            category="laboratory",
            kind="service_request",
            code=code_snomed_fasting_glucose,
            diagnostic_report_codes=[code_loinc_fasting_glucose_serum],
        ),
        facility,
        user,
        slug="fasting_glucose",
        specimen_requirements=[blood_glucose_specimen_definition.id],
        observation_result_requirements=[
            fasting_blood_glucose_observation_definition.id
        ],
        locations=[bio_chemistry_lab_location.id],
        charge_item_definitions=[fasting_blood_glucose_charge_definition.id],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="activity_definition"
        ),
    )
    create_object(
        BaseActivityDefinitionSpec(
            id="76c88bae-f4a4-4200-86b9-77f9a26d1a13",
            title="Complete Blood Count (CBC) Panel",
            status="active",
            description="A Complete Blood Count (CBC) is a common laboratory test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), white blood cells (WBC), hemoglobin, hematocrit, and platelets.",
            usage="test that evaluates the overall health status by measuring multiple components of blood including red blood cells (RBC), ",
            classification="laboratory",
            category="laboratory",
            kind="service_request",
            code=code_snomed_cbc,
            diagnostic_report_codes=[code_loinc_cbc_panel],
        ),
        facility,
        user,
        slug="complete_blood_count",
        specimen_requirements=[cbc_specimen_definition.id],
        observation_result_requirements=[cbc_observation_definition.id],
        locations=[bio_chemistry_lab_location.id],
        charge_item_definitions=[cbc_charge_definition.id],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="activity_definition"
        ),
    )
    create_object(
        BaseActivityDefinitionSpec(
            title="Lipid Panel",
            status="active",
            derived_from_uri="urn:activity:lipid-panel",
            description="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
            usage="A comprehensive blood test measuring cholesterol and triglyceride levels to assess cardiovascular health.",
            classification="laboratory",
            category="laboratory",
            kind="service_request",
            code=code_snomed_lipid_panel,
            diagnostic_report_codes=[code_loinc_lipid_panel],
        ),
        facility,
        user,
        slug="lipid_panel",
        specimen_requirements=[lipid_panel_specimen_definition.id],
        observation_result_requirements=[lipid_panel_observation_definition.id],
        locations=[bio_chemistry_lab_location.id],
        charge_item_definitions=[lipid_panel_charge_definition.id],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="activity_definition"
        ),
    )
    create_object(
        BaseActivityDefinitionSpec(
            title="Urinalysis",
            status="active",
            description="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
            usage="A diagnostic test analyzing urine's physical, chemical, and microscopic properties to detect various conditions.",
            classification="laboratory",
            category="laboratory",
            kind="service_request",
            code=code_snomed_urine,
            diagnostic_report_codes=[code_loinc_urine],
        ),
        facility,
        user,
        slug="urinalysis",
        specimen_requirements=[urinalysis_specimen_definition.id],
        observation_result_requirements=[urinalysis_observation_definition.id],
        locations=[bio_chemistry_lab_location.id],
        charge_item_definitions=[urinalysis_charge_definition.id],
        category=create_resource_category(
            facility, title="Lab Tests", resource_type="activity_definition"
        ),
    )
