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
