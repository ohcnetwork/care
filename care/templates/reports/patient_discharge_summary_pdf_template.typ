{% load static %}
{% load data_formatting_extras %}
{% load discharge_summary_utils %}

#set page("a4",margin: 40pt)
#set text(font: "DejaVu Sans",size: 10pt,hyphenate: true, fallback: true)
#let mygray = luma(100)

#let frame(stroke) = (x, y) => (
    left: if x > 0 { 0pt } else { stroke },
    right: stroke,
    top: if y < 2 { stroke } else { 0pt },
    bottom: stroke,
)

#set table(
    fill: (_, y) => if calc.odd(y) { rgb("EAF2F5") },
    stroke: frame(rgb("21222C")),
)

#let facility_name="{{encounter.facility.name}}"

#align(center, text(24pt,weight: "bold")[= #facility_name])

#line(length: 100%, stroke: mygray)

#grid(
    columns: (auto, 1fr),
    row-gutter: 1em,
    align: (left, right),
    text(size: 15pt)[= {{ encounter.encounter_class|discharge_summary_display }}],
    grid.cell(align: right, rowspan: 2)[#image("{{ logo_path }}", width: 32%)],
    [#text(fill: mygray, weight: 500)[*Created on {{date}}*]]
)

#line(length: 100%, stroke: mygray)

#show grid.cell.where(x: 0): set text(fill: mygray,weight: "bold")
#show grid.cell.where(x: 2): set text(fill: mygray,weight: "bold")

#grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    row-gutter: 1.5em,
    [Full name:], "{{patient.name}}",
    [Gender:], "{{patient.gender|field_name_to_label }}",
    [Age:], "{{patient.get_age }}",
    [Blood Group:], "{{patient.blood_group|field_name_to_label }}",
    [Phone Number:], "{{patient.phone_number }}",
    [Ration Card Category:], "{{patient.get_ration_card_category_display|format_empty_data }}",
    [Address:], grid.cell(colspan: 3, "{{patient.address }}"),
)

#line(length: 100%, stroke: mygray)

#align(left, text(18pt)[== Visit Details])
#text("")
#grid(
    columns: (1.1fr, 2fr),
    row-gutter: 1.2em,
    align: (left),
    [Route to Facility:], "{{ encounter.hospitalization.admit_source|admit_source_display }}",
    {% if encounter.encounter_class == "imp" %}
        [Admitted To:], "{{ encounter.facility.name|format_empty_data }}", // TODO: show bed info instead of facility name
        [Duration of Admission:], "{{admission_duration|format_empty_data}}",
        [Date of admission:], "{{ encounter.period.start|parse_iso_datetime|format_empty_data }}",
        [IP No:], "{{ encounter.external_identifier }}",
    {% else %}
        [OP No:], "{{ encounter.external_identifier  }}",
    {% endif %}
    [Diagnosis:],[#stack(
        dir: ttb,
        spacing: 10pt,
        {% for diagnose in diagnoses %}
            "{{ diagnose.code.display  }} ({{diagnose.verification_status }})",
        {% endfor %}
    )],
    [Principal Diagnosis:],
    {% if principal_diagnosis %}
        "{{ principal_diagnosis.code.display }}",
    {% else %}
        "N/A",
    {% endif %}
    [Symptoms:], [#stack(
        dir: ttb,
        spacing: 10pt,
        {% if symptoms %}
            {% for symptom in symptoms %}
                "{{ symptom.code.display }}",
            {% endfor %}
        {% else %}
            "Asymptomatic"
        {% endif %}
    )],
    [Reported Allergies:],
    {% if allergies %}
        [#stack(
            dir: ttb,
            spacing: 10pt,
            {% for allergy in allergies %}
                "{{ allergy.code.display }}",
            {% endfor %}
        )],
    {% else %}
        "N/A",
    {% endif %}
)

#text("")

#align(center, [#line(length: 40%, stroke: mygray)])

// TODO: add comorbidity info

{% if medication_requests %}
    #align(left, text(14pt,weight: "bold",)[=== Medication Requests:])
    #table(
        columns: (1fr,),
        inset: 10pt,
        align: horizon,
        stroke: 1pt,
        table.header(
            align(center, text([*MEDICATION REQUESTS*]))
        ),
        {% for medication in medication_requests %}
            [#grid(
                columns: (1fr, 3fr),
                row-gutter: 1.2em,
                align: (left),
                [Name:], "{{ medication.meta.medication.display }} ({{ medication.meta.medication.system }} {{ medication.meta.medication.code }})",
                [Dosage:], "{{ medication|medication_dosage_display|format_empty_data }}",
                {% if medication.created_by %}
                    [Prescribed By:], "{{ medication.created_by.fullname|default:medication.created_by.username }}",
                {% endif %}
                [Date:], "{{ medication.authored_on|default:medication.created_date }}",
            )],
        {% endfor %}
    )

    #align(center, [#line(length: 40%, stroke: mygray)])

{% endif %}


{% if observations %}
    #align(left, text(14pt,weight: "bold")[=== Observations:])
    #table(
        columns: (1fr,),
        inset: 10pt,
        align: horizon,
        stroke: 1pt,
        table.header(
            align(center, text([*OBSERVATION DETAILS*]))
        ),
        {% for observation in observations %}
            {% if observation.main_code.display and observation|observation_value_display %}
                [#grid(
                    columns: (1fr, 3fr),
                    row-gutter: 1.2em,
                    align: (left),
                    [Name:], "{{ observation.main_code.display }} ({{ observation.main_code.system }} {{ observation.main_code.code }})",
                    [Value:], "{{ observation|observation_value_display|field_name_to_label|format_empty_data }}",
                    {% if observation.body_site %}
                        [Body Site:], "{{ observation.body_site.display }}",
                    {% endif %}
                    [Date:], "{{ observation.effective_datetime  }}",
                    [Data Entered By:], "{{ observation.data_entered_by.fullname|default:observation.data_entered_by.username }}",
                    {% if observation.note %}
                        [Note:], "{{ observation.note }}",
                    {% endif %}
                )],
            {% endif %}
        {% endfor %}
    )

    #align(center, [#line(length: 40%, stroke: mygray)])
{% endif %}


{% if encounter.hospitalization and encounter.hospitalization.discharge_disposition %}
    #align(left, text(18pt,)[== Discharge Summary])
    #grid(
        columns: (1fr,3fr),
        row-gutter: 1.2em,
        align: (left),
        [Discharge Date:], "{{ encounter.period.end|parse_iso_datetime|format_empty_data }}",
        [Discharge Disposition:], "{{ encounter.hospitalization.discharge_disposition|discharge_disposition_display }}",
    )

    #align(center, [#line(length: 40%, stroke: mygray)])
{% endif %}


#align(right)[#text(12pt,fill: mygray)[*Care Team* :] #text(10pt,weight: "bold")[{% if care_team %}
    {% for member in care_team %}
        {{ member }}
    {% endfor %}
{% else %}
    -
{% endif %}]]


{% if files %}
    #align(left, text(18pt,)[== Annexes])
    #align(left, text(14pt,weight: "bold",)[=== Uploaded Files:])

    #table(
        columns: (1fr, 1fr,),
        inset: 10pt,
        align: horizon,
        table.header(
            [*UPLOADED AT*], [*NAME*],
        ),
        {% for file in files %}
            "{{file.modified_date }}", text(hyphenate: true)["{{file.name }}"],
        {% endfor %}
    )
{% endif %}

#text("")
#line(length: 100%, stroke: mygray)
#text("")
{% if discharge_summary_advice %}

    = Discharge Summary Advice
    #text()[```{{ discharge_summary_advice }}```]
{% endif %}
