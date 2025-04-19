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
