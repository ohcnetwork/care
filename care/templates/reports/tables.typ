{% for table in tables %}
#align(left, text(14pt, weight: "bold")[=== {{ table.title }}:])

#table(
columns: (
    {% for _ in table.data.table.0 %}
        auto{% if not forloop.last %}, {% endif %}
    {% endfor %}
),
    stroke: 0.5pt,
    inset: 8pt,
    align: horizon,

    // Render header
    table.header(
        {% for col in table.data.table.0 %}
            [*{{ col|upper }}*],
        {% endfor %}
    ),

    // Render rows
    {% for row in table.data.table|slice:"1:" %}
        {% for cell in row %}
        [
            {{ cell|default:"-" }}
                    ],

        {% endfor %}
    {% endfor %}
)

#v(12pt)
#align(center, [#line(length: 50%, stroke: 0.5pt)])
#v(16pt)
{% endfor %}
