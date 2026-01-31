curl -X POST 'http://127.0.0.1:9000/api/v1/fhir/bundle/process/' \
  -H 'Content-Type: application/json' \
  -H 'authorization: Basic YWRtaW46YWRtaW4=' \
  -d '{
    "encounter": "169a0cde-0667-4e15-9950-16163b1f2b9b",
    "fail_on_error": true,
    "bundle": {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-1",
                    "clinicalStatus": {
                        "coding": [{"code": "active"}]
                    },
                    "verificationStatus": {
                        "coding": [{"code": "confirmed"}]
                    },
                    "category": [
                        {"coding": [{"code": "encounter-diagnosis"}]}
                    ],
                    "severity": {
                        "coding": [{"code": "moderate"}]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "38341003",
                            "display": "Hypertension"
                        }]
                    },
                    "onsetDateTime": "2024-01-15T10:00:00Z",
                    "note": [{"text": "Patient has history of hypertension"}]
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-2",
                    "clinicalStatus": {
                        "coding": [{"code": "active"}]
                    },
                    "verificationStatus": {
                        "coding": [{"code": "confirmed"}]
                    },
                    "category": [
                        {"coding": [{"code": "encounter-diagnosis"}]}
                    ],
                    "severity": {
                        "coding": [{"code": "mild"}]
                    },
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "73211009",
                            "display": "Diabetes mellitus"
                        }]
                    },
                    "onsetAge": {"value": 45},
                    "note": [{"text": "Type 2 diabetes, well controlled"}]
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-1",
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure"
                        }]
                    },
                    "effectiveDateTime": "2024-01-20T09:30:00Z",
                    "valueQuantity": {
                        "value": 140,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    },
                    "interpretation": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": "H",
                            "display": "High"
                        }]
                    }],
                    "referenceRange": [{
                        "low": {"value": 90, "unit": "mmHg"},
                        "high": {"value": 120, "unit": "mmHg"},
                        "type": {"coding": [{"code": "normal"}]}
                    }]
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-2",
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure"
                        }]
                    },
                    "effectiveDateTime": "2024-01-20T09:30:00Z",
                    "valueQuantity": {
                        "value": 90,
                        "unit": "mmHg",
                        "system": "http://unitsofmeasure.org",
                        "code": "mm[Hg]"
                    }
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "observation-3",
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "4548-4",
                            "display": "Hemoglobin A1c"
                        }]
                    },
                    "effectiveDateTime": "2024-01-20T10:00:00Z",
                    "valueQuantity": {
                        "value": 6.8,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "note": [{"text": "Slightly elevated, continue monitoring"}]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-request-1",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "category": [{"coding": [{"code": "inpatient"}]}],
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "387458008",
                            "display": "Aspirin"
                        }]
                    },
                    "authoredOn": "2024-01-20T11:00:00Z",
                    "dosageInstruction": [{
                        "sequence": 1,
                        "text": "Take 1 tablet daily",
                        "timing": {
                            "repeat": {
                                "frequency": 1,
                                "period": 1,
                                "periodUnit": "d",
                                "boundsDuration": {
                                    "value": 30,
                                    "code": "d"
                                }
                            },
                            "code": {"coding": [{"code": "daily", "display": "Daily"}]}
                        },
                        "asNeededBoolean": false,
                        "route": {
                            "coding": [{
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": "Oral"
                            }]
                        },
                        "doseAndRate": [{
                            "type": {"coding": [{"code": "ordered"}]},
                            "doseQuantity": {
                                "value": 75,
                                "unit": "mg",
                                "code": "mg"
                            }
                        }]
                    }],
                    "note": [{"text": "For cardiovascular protection"}]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-request-2",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "category": [{"coding": [{"code": "inpatient"}]}],
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "372756006",
                            "display": "Metformin"
                        }]
                    },
                    "authoredOn": "2024-01-20T11:00:00Z",
                    "dosageInstruction": [{
                        "sequence": 1,
                        "text": "Take 500mg twice daily with meals",
                        "timing": {
                            "repeat": {
                                "frequency": 2,
                                "period": 1,
                                "periodUnit": "d",
                                "boundsDuration": {
                                    "value": 90,
                                    "code": "d"
                                }
                            },
                            "code": {"coding": [{"code": "BID", "display": "Twice daily"}]}
                        },
                        "asNeededBoolean": false,
                        "route": {
                            "coding": [{
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": "Oral"
                            }]
                        },
                        "doseAndRate": [{
                            "type": {"coding": [{"code": "ordered"}]},
                            "doseQuantity": {
                                "value": 500,
                                "unit": "mg",
                                "code": "mg"
                            }
                        }]
                    }],
                    "note": [{"text": "For blood sugar control"}]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-request-3",
                    "status": "active",
                    "intent": "order",
                    "priority": "urgent",
                    "category": [{"coding": [{"code": "inpatient"}]}],
                    "medicationCodeableConcept": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "387517004",
                            "display": "Lisinopril"
                        }]
                    },
                    "authoredOn": "2024-01-20T11:00:00Z",
                    "dosageInstruction": [{
                        "sequence": 1,
                        "text": "Take 10mg once daily in the morning",
                        "timing": {
                            "repeat": {
                                "frequency": 1,
                                "period": 1,
                                "periodUnit": "d",
                                "boundsDuration": {
                                    "value": 30,
                                    "code": "d"
                                }
                            },
                            "code": {"coding": [{"code": "QAM", "display": "Every morning"}]}
                        },
                        "asNeededBoolean": false,
                        "route": {
                            "coding": [{
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": "Oral"
                            }]
                        },
                        "doseAndRate": [{
                            "type": {"coding": [{"code": "ordered"}]},
                            "doseQuantity": {
                                "value": 10,
                                "unit": "mg",
                                "code": "mg"
                            }
                        }]
                    }],
                    "note": [{"text": "ACE inhibitor for hypertension"}]
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "allergy-1",
                    "clinicalStatus": {
                        "coding": [{"code": "active"}]
                    },
                    "verificationStatus": {
                        "coding": [{"code": "confirmed"}]
                    },
                    "type": "allergy",
                    "category": ["medication"],
                    "criticality": "high",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "91936005",
                            "display": "Penicillin allergy"
                        }]
                    },
                    "onsetDateTime": "2010-05-01T00:00:00Z",
                    "recordedDate": "2024-01-20T12:00:00Z",
                    "note": [{"text": "Causes severe rash and difficulty breathing"}]
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "allergy-2",
                    "clinicalStatus": {
                        "coding": [{"code": "active"}]
                    },
                    "verificationStatus": {
                        "coding": [{"code": "confirmed"}]
                    },
                    "type": "intolerance",
                    "category": ["food"],
                    "criticality": "low",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "91935009",
                            "display": "Lactose intolerance"
                        }]
                    },
                    "onsetAge": {"value": 30},
                    "recordedDate": "2024-01-20T12:00:00Z",
                    "note": [{"text": "Causes GI discomfort"}]
                }
            },
            {
                "resource": {
                    "resourceType": "ServiceRequest",
                    "id": "service-request-1",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "category": [{"coding": [{"code": "laboratory"}]}],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "2093-3",
                            "display": "Cholesterol total"
                        }],
                        "text": "Lipid Panel"
                    },
                    "occurrenceDateTime": "2024-01-21T08:00:00Z",
                    "patientInstruction": "Fasting required for 12 hours before test",
                    "note": [{"text": "Annual lipid screening"}]
                }
            },
            {
                "resource": {
                    "resourceType": "ServiceRequest",
                    "id": "service-request-2",
                    "status": "active",
                    "intent": "order",
                    "priority": "urgent",
                    "category": [{"coding": [{"code": "imaging"}]}],
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "77477000",
                            "display": "Chest X-ray"
                        }],
                        "text": "Chest X-ray PA and Lateral"
                    },
                    "bodySite": [{
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "51185008",
                            "display": "Thorax"
                        }]
                    }],
                    "occurrenceDateTime": "2024-01-20T14:00:00Z",
                    "note": [{"text": "Rule out pneumonia"}]
                }
            },
            {
                "resource": {
                    "resourceType": "ServiceRequest",
                    "id": "service-request-3",
                    "status": "active",
                    "intent": "order",
                    "priority": "routine",
                    "category": [{"coding": [{"code": "procedure"}]}],
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "29303009",
                            "display": "Electrocardiogram"
                        }],
                        "text": "12-lead ECG"
                    },
                    "occurrenceDateTime": "2024-01-20T15:00:00Z",
                    "patientInstruction": "Remove metal jewelry before procedure",
                    "note": [{"text": "Baseline cardiac assessment"}]
                }
            }
        ]
    }
}'
