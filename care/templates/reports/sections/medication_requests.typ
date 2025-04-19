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
