{% comment %}
  table.typ
  Renders a single table section with:
    - title:   String
    - columns: List of header strings
    - rows:    List of lists, each inner list is one data row
{% endcomment %}

#align(left, text(14pt, weight: "bold")[=== {{ title }}:])

#table(
  columns: (
    {# one “auto” per column #}
    {% for _ in columns %}
      auto{% if not forloop.last %}, {% endif %}
    {% endfor %}
  ),
  stroke: 0.5pt,
  inset: 8pt,
  align: horizon,

  // header row
  table.header(
    {% for col in columns %}
      [*{{ col|upper }}*]{% if not forloop.last %}, {% endif %}
    {% endfor %}
  ),

  // data rows
  {% for row in rows %}
    {% for cell in row %}
      [{{ cell|default:"-" }}]{% if not forloop.last or not forloop.parentloop.last %}, {% endif %}
    {% endfor %}
  {% endfor %}
)

#v(12pt)
#align(center, [#line(length: 50%, stroke: 0.5pt)])
#v(16pt)
