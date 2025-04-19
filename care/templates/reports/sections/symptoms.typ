#align(left, text(14pt,weight: "bold")[=== Symptoms:])
#table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
        align(center, text([*SYMPTOMS DETAILS*]))
    ),
    {% for symptom in symptoms %}
            [#grid(
                columns: (1fr, 3fr),
                row-gutter: 1.2em,
                align: (left),
                [Symptom:], "{{ symptom.code.display }}",
                [Severity:], "{{ symptom.clinical_status }}",
                [Status:], "{{ symptom.clinical_status }}",
                [Verification:], "{{ symptom.verification_status  }}",
                [Onset:], "{{ symptom.onset.onset_datetime  }}",
                [Notes:], text(hyphenate: true)["{{ symptom.note }}"],
                [Logged by:], "{{ symptom.created_by.full_name }}",
            )],
    {% endfor %}
)

#align(center, [#line(length: 40%, stroke: mygray)])
