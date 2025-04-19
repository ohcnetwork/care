#align(left, text(14pt,weight: "bold")[=== Allergies:])
#table(
    columns: (1fr,),
    inset: 10pt,
    align: horizon,
    stroke: 1pt,
    table.header(
        align(center, text([*ALLERGIES DETAILS*]))
    ),
    {% for allergy in allergies %}
            [#grid(
                columns: (1fr, 3fr),
                row-gutter: 1.2em,
                align: (left),
                [Allergen:], "{{ allergy.code.display }}",
                [Status:], "{{ allergy.clinical_status }}",
                [Criticality:], "{{ allergy.criticality }}",
                [Verification:], "{{ allergy.verification_status  }}",
                [Notes:], text(hyphenate: true)["{{ allergy.note }}"],
                [Logged by:], "{{ allergy.created_by.full_name }}",
            )],
    {% endfor %}
)

#align(center, [#line(length: 40%, stroke: mygray)])
