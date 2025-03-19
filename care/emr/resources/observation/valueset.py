from care.emr.registries.care_valueset.care_valueset import CareValueset
from care.emr.resources.common.valueset import ValueSetCompose
from care.emr.resources.valueset.spec import ValueSetStatusOptions

CARE_OBSERVATION_VALUSET = CareValueset(
    "Observation", "system-observation", ValueSetStatusOptions.active.value
)


CARE_OBSERVATION_VALUSET.register_valueset(
    ValueSetCompose(include=[{"system": "http://loinc.org"}])
)

CARE_OBSERVATION_VALUSET.register_as_system()


CARE_BODY_SITE_VALUESET = CareValueset(
    "Body Site", "system-body-site-observation", ValueSetStatusOptions.active.value
)


CARE_BODY_SITE_VALUESET.register_as_system()

CARE_BODY_SITE_VALUESET.register_valueset(
    ValueSetCompose(
        include=[
            {
                "system": "http://snomed.info/sct",
                "concept": [
                    {"code": "53075003", "display": "Distal phalanx of hallux"},
                    {"code": "76986006", "display": "Distal phalanx of second toe"},
                    {"code": "65258003", "display": "Distal phalanx of third toe"},
                    {"code": "54333003", "display": "Distal phalanx of fourth toe"},
                    {"code": "10770001", "display": "Distal phalanx of fifth toe"},
                    {
                        "code": "363670009",
                        "display": "Interphalangeal joint structure of great toe",
                    },
                    {
                        "code": "371216008",
                        "display": "Distal interphalangeal joint of second toe",
                    },
                    {
                        "code": "371219001",
                        "display": "Distal interphalangeal joint of third toe",
                    },
                    {
                        "code": "371205001",
                        "display": "Distal interphalangeal joint of fourth toe",
                    },
                    {
                        "code": "371203008",
                        "display": "Distal interphalangeal joint of fifth toe",
                    },
                    {
                        "code": "371292009",
                        "display": "Proximal interphalangeal joint of second toe",
                    },
                    {
                        "code": "371255009",
                        "display": "Proximal interphalangeal joint of third toe",
                    },
                    {
                        "code": "371288002",
                        "display": "Proximal interphalangeal joint of fourth toe",
                    },
                    {
                        "code": "371284000",
                        "display": "Proximal interphalangeal joint of fifth toe",
                    },
                    {"code": "67169006", "display": "Head of first metatarsal bone"},
                    {"code": "9677004", "display": "Head of second metatarsal bone"},
                    {"code": "46971007", "display": "Head of third metatarsal bone"},
                    {"code": "3134008", "display": "Head of fourth metatarsal bone"},
                    {"code": "71822005", "display": "Head of fifth metatarsal bone"},
                    {"code": "89221001", "display": "Base of first metatarsal bone"},
                    {"code": "90894004", "display": "Base of second metatarsal bone"},
                    {"code": "89995006", "display": "Base of third metatarsal bone"},
                    {"code": "15368009", "display": "Base of fourth metatarsal bone"},
                    {"code": "30980004", "display": "Base of fifth metatarsal bone"},
                    {
                        "code": "38607000",
                        "display": "Styloid process of fifth metatarsal bone",
                    },
                    {"code": "2979003", "display": "Medial cuneiform bone"},
                    {"code": "19193007", "display": "Intermediate cuneiform bone"},
                    {"code": "67411009", "display": "Lateral cuneiform bone"},
                    {"code": "81012005", "display": "Bone structure of cuboid"},
                    {"code": "75772009", "display": "Bone structure of navicular"},
                    {"code": "67453005", "display": "Bone structure of talus"},
                    {"code": "80144004", "display": "Bone structure of calcaneum"},
                    {"code": "6417001", "display": "Medial malleolus"},
                    {"code": "113225006", "display": "Lateral malleolus of fibula"},
                    {"code": "22457002", "display": "Head of fibula"},
                    {"code": "45879002", "display": "Tibial tuberosity"},
                    {"code": "122474001", "display": "Medial condyle of femur"},
                    {"code": "122475000", "display": "Lateral condyle of femur"},
                    {"code": "69030007", "display": "Ischial tuberosity"},
                    {"code": "29850006", "display": "Iliac crest"},
                ],
            },
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "442083009"}],
            },
        ]
    )
)


CARE_OBSERVATION_COLLECTION_METHOD = CareValueset(
    "Observation Method", "system-collection-method", ValueSetStatusOptions.active.value
)

CARE_OBSERVATION_COLLECTION_METHOD.register_valueset(
    ValueSetCompose(
        include=[
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "272394005"}],
            },
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "129264002"}],
            },
            {
                "system": "http://snomed.info/sct",
                "filter": [{"property": "concept", "op": "is-a", "value": "386053000"}],
            },
        ]
    )
)

CARE_OBSERVATION_COLLECTION_METHOD.register_as_system()


CARE_UCUM_UNITS = CareValueset(
    "UCUM Units", "system-ucum-units", ValueSetStatusOptions.active.value
)

CARE_UCUM_UNITS.register_valueset(
    ValueSetCompose(include=[{"system": "http://unitsofmeasure.org"}])
)

CARE_UCUM_UNITS.register_as_system()
