#align(left, text(14pt,weight: "bold")[=== Diagnoses:])
#table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
        align(center, text([*DIAGNOSES DETAILS*]))
    ),
    {% for diagnosis in diagnoses %}
            [#grid(
                columns: (1fr, 3fr),
                row-gutter: 1.2em,
                align: (left),
                [Diagnosis:], "{{ diagnosis.code.display }}",
                [Severity:], "{{ diagnosis.clinical_status }}",
                [Status:], "{{ diagnosis.clinical_status }}",
                [Verification:], "{{ diagnosis.verification_status  }}",
                [Onset:], "{{ diagnosis.onset.onset_datetime  }}",
                [Notes:], text(hyphenate: true)["{{ diagnosis.note }}"],
                [Logged by:], "{{ diagnosis.created_by.full_name }}",
            )],
    {% endfor %}
)

#align(center, [#line(length: 40%, stroke: mygray)])
