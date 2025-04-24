{# templates/typst/sections/list.typ #}
{% comment %}
  Renders a two-column key/value grid.
  Expects in context:
    - title: String
    - rows:  List of [label, value] pairs
{% endcomment %}

#align(left, text(14pt, weight: "bold")[=== {{ title }}:])

#grid(
  columns: (auto, auto),
  row-gutter: 1.5em,
  column-gutter: 2em,
  {# iterate each label/value pair #}
  {% for label, value in rows %}
    [{{ label }}:], "{{ value }}"{% if not forloop.last %}, {% endif %}
  {% endfor %}
)

#line(length: 100%, stroke: mygray)
