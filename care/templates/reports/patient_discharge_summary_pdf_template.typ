{% load static %}
{% load filters static %}
{% load prescription_tags %}


#set page("a4",margin: 40pt)
#set text(font: "DejaVu Sans",size: 10pt,hyphenate: true)
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

#align(center, text(24pt,weight: "bold")[= {{patient.facility.name}}])  // Todo : Convert it to not use content mode

#line(length: 100%, stroke: mygray)

#grid(
    columns: (auto, 1fr),
    row-gutter: 1em,
    align: (left, right),
    text(size: 15pt)[= Patient Discharge Summary],
    grid.cell(align: right, rowspan: 2)[#scale(x:90%, y:90%, reflow: true)[#image("{{ logo_path }}")]],
    [#text(fill: mygray, weight: 500)[*Created on {{date}}*]]
)


#line(length: 100%, stroke: mygray)

#show grid.cell.where(x: 0): set text(fill: mygray,weight: "bold")
#show grid.cell.where(x: 2): set text(fill: mygray,weight: "bold")

#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  row-gutter: 1.5em,
  [Full name:], "{{patient.name}}",
  [Gender:], "{{patient.get_gender_display}}",
  [Age:], "{{patient.get_age}}",
  [Blood Group:], "{{patient.blood_group}}",
  [Phone Number:], "{{patient.phone_number}}",
  [Ration Card Category:], "{{patient.get_ration_card_category_display}}",
  [Address:], grid.cell(colspan: 3, "{{patient.address}}"),
)

#line(length: 100%, stroke: mygray)

#align(left, text(18pt)[== Admission Details])
#text("")
#grid(
  columns: (1.1fr, 2fr),
  row-gutter: 1.2em,
  align: (left),
  [Route to Facility:], "{{ consultation.get_route_to_facility_display | field_name_to_label }}",
  [Decision after consultation:], "{{ consultation.get_suggestion_display | field_name_to_label }}",
  [Duration of Admission:], "temp",  // TODO : need to add it
  {% if consultation.icu_admission_date %}
  [ICU Admission Date & Time:], "{{ consultation.icu_admission_date }}",
  {% endif %}
  {% if consultation.suggestion == 'A' %}
  [Date of admission:], "{{ consultation.encounter_date }}",
  {% elif consultation.suggestion == 'R' %}
  [Referred to:], "{{ consultation.referred_to.name }}",
  {% elif consultation.suggestion == 'DD' %}
  [Cause of death:], "{{ consultation.discharge_notes }}",
  [Date and time of death:], "{{ consultation.death_datetime }}",
  [Death Confirmed by:], "{{ consultation.death_confirmed_by }}",
  {% endif %}
  [IP No:], "{{ consultation.patient_no }}",
  [Weight:], "{{ consultation.weight }} kg",
  [Height:], "{{ consultation.height }} cm",
  [Diagnosis at admission:],[#stack(
    dir: ttb,
    spacing: 10pt,
    {% for diagnose in diagnoses %}
      "{{ diagnose.label }}",
    {% endfor %}
  )
  ],
  [Reason for admission:],[#stack(
    dir: ttb,
    spacing: 10pt,
    {% for diagnose in primary_diagnoses %}
      "{{ diagnose.label }}",
    {% endfor %}
  )
  ],
  [Symptoms at admission],[#stack(
    dir: ttb,
    spacing: 10pt,
    {% for symptom in symptoms %}
      {% if symptom.symptom == 9 %}
        "{{ symptom.other_symptom }}",
      {% else %}
        "{{ symptom.get_symptom_display }}",
      {% endif %}
    {% endfor %}
  )
  ],
  [Reported Allergies:], "{{ patient.allergies }}",
)

#text("\n")

#align(center, [#line(length: 40%, stroke: mygray)])


{% if medical_history %}

#align(left, text(14pt,weight: "bold",)[=== Medication History:])

#table(
  columns: (1.5fr, 3.5fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*COMORBIDITY*], [*DETAILS*],
  ),
  {% for disease in medical_history %}
  "{{disease.get_disease_display}}", "{{disease.details}}",
  {% endfor %}
)
#align(center, [#line(length: 40%, stroke: mygray,)])
{% endif %}


{% if consultation.suggestion != 'DD' %}
  #align(left, text(18pt,)[== Treatment Summary])
  #text("")

  {% if patient.disease_status == 2 %}
    #grid(
      columns: (1fr, 1fr),
      gutter: 1.4em,
      align: (left),
      [COVID Disease Status:], [Positive],
      {% if patient.date_of_result %}
        [Test Result Date:], "{{ patient.date_of_result.date }}",
      {% endif %}
      [Vaccinated against COVID:], [
        {% if patient.is_vaccinated %}
          Yes
        {% else %}
          No
        {% endif %}
      ],
    )
  {% endif %}

  {% if prescriptions %}
  #align(left, text(14pt,weight: "bold",)[=== Prescription Medication:])
  #table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
      align(center, text([*MEDICATION DETAILS*]))
    ),
    {% for prescription in prescriptions %}
    [#grid(
      columns: (0.5fr, 9.5fr),
      row-gutter: 1.2em,
      align: (left),
      "{{ forloop.counter }}",
      "{{ prescription|format_prescription }}",
    )],
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray,)])
  {% endif %}

  {% if consultation.investigation %}
  #align(left, text(14pt,weight: "bold",)[=== Investigations Conducted:])

  #table(
    columns: (1.5fr, 1fr, 1.5fr),
    inset: 10pt,
    align: horizon,
    table.header(
      [*TYPE*], [*TIME*], [*NOTES*]
    ),
    {% for investigation in consultation.investigation %}
    "{{ investigation.type|join:", " }}",
    "{% if investigation.repetitive %}every {{ investigation.frequency }}{% else %}{{ investigation.time|date:"DATETIME_FORMAT" }}{% endif %}",
    "{{ investigation.notes }}",
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray,)])
  {% endif %}

  {% if consultation.procedure %}
  #align(left, text(14pt,weight: "bold",)[=== Procedures Conducted:])

  #table(
    columns: (1fr, 1fr, 2fr),
    inset: 10pt,
    align: horizon,
    table.header(
      [*PROCEDURE*], [*TIME*], [*NOTES*]
    ),
    {% for procedure in consultation.procedure %}
    "{{ procedure.procedure }}", "{% if procedure.repetitive %} every {{procedure.frequency}} {% else %} {{procedure.time|parse_datetime}} {% endif %}", "{{ procedure.notes }}",
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray,)])
  {% endif %}


  {% if samples %}
  #align(left, text(14pt,weight: "bold",)[=== Lab Reports:])

  #table(
    columns: (1fr, 1fr, 1fr,1fr),
    inset: 10pt,
    align: horizon,
    table.header(
      [*REQUESTED ON*], [*SAMPLE TYPE*], [*LABEL*],[*RESULT*],
    ),
    {% for sample in samples %}
    "{{ sample.created_date }}", "{{ sample.get_sample_type_display }}", "{{ sample.icmr_label }}","{{ sample.get_result_display }}",
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray,)])
  {% endif %}


  {% if investigations %}
  #align(left, text(14pt,weight: "bold")[=== Investigation History:])
  #table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
      align(center, text([*INVESTIGATION DETAILS*]))
    ),
    {% for investigation in investigations %}
    [#grid(
      columns: (1fr, 3fr),
      row-gutter: 1.2em,
      align: (left),
      [Group:], "{{ investigation.investigation.groups.first }}",
      [Name:], "{{ investigation.investigation.name }}",
      [Result:], [{% if investigation.value %}{{ investigation.value }}{% else %}{{ investigation.notes }}{% endif %}],
      [Range:], [{% if investigation.investigation.min_value and investigation.investigation.max_value %}
        {{ investigation.investigation.min_value }} - {{ investigation.investigation.max_value }}
        {% else %}
        -
        {% endif %}
        {% if investigation.investigation.unit %}
        {{ investigation.investigation.unit }}
        {% endif %}
      ],
      [Date:], "{{ investigation.created_date }}",
    )],
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray)])
  {% endif %}

{% endif %}

{% if hcx %}
#align(left, text(14pt,weight: "bold")[=== Health Insurance Details])

#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*INSURER NAME*], [*ISSUER ID*], [*MEMBER ID*], [*POLICY ID*],
  ),
  {% for policy in hcx %}
  "{{policy.insurer_name}}", "{{policy.insurer_id}}", "{{policy.subscriber_id}}", "{{policy.policy_id}}",
  {% endfor %}
)
#align(center, [#line(length: 40%, stroke: mygray)])

{% endif %}

#align(left, text(18pt,)[== Discharge Summary])
#grid(
  columns: (1fr,3fr),
  row-gutter: 1.2em,
  align: (left),
  [Discharge Date:], "{{consultation.discharge_date}}",
  [Discharge Reason:], "{{consultation.get_discharge_reason_display}}",
)

{% if consultation.new_discharge_reason == 1 %}
  {% if discharge_prescriptions %}
  #align(left, text(14pt,weight: "bold",)[=== Discharge Prescription Medication:])
  #table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
      align(center, text([*MEDICATION DETAILS*]))
    ),
    {% for prescription in discharge_prescriptions %}
    [#grid(
      columns: (0.5fr, 9.5fr),
      row-gutter: 1.2em,
      align: (left),
      "{{ forloop.counter }}",
      "{{ prescription|format_prescription }}",
    )],
    {% endfor %}
  )

  #align(center, [#line(length: 40%, stroke: mygray,)])
  {% endif %}

  {% elif consultation.new_discharge_reason == 2 %}
  {% elif consultation.new_discharge_reason == 3 %}
  {% elif consultation.new_discharge_reason == 4 %}

{%endif%}

#grid(
  columns: (1fr,3fr),
  row-gutter: 1.2em,
  align: (left),
  [Discharge Notes:], "{{consultation.discharge_notes}}",
)

#align(right)[#text(12pt,fill: mygray)[*Treating Physician* :] #text(10pt,weight: "bold")[{% if consultation.treating_physician %}
    {{ consultation.treating_physician.first_name }} {{ consultation.treating_physician.last_name }}
  {% else %}
    -
  {% endif %}]]


{% if files %}
#align(center, [#line(length: 40%, stroke: mygray,)])

#align(left, text(18pt,)[== Annexes])
#text("")
#align(left, text(14pt,weight: "bold",)[=== Uploaded Files:])

#table(
  columns: (1fr, 1fr,),
  inset: 10pt,
  align: horizon,
  table.header(
    [*UPLOADED AT*], [*NAME*],
  ),
  {% for file in files %}
  "{{file.modified_date}}", "{{file.name}}",
  {% endfor %}
)

{% endif %}
#line(length: 100%, stroke: mygray)
