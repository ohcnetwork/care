#align(left, text(14pt, weight: "bold")[=== {{ title }}:])

{% for object_rows in rows %}
#grid(
  columns: (auto, auto),
  row-gutter: 1.5em,
  column-gutter: 2em,
  {% for label, value in object_rows %}
    [{{ label }}:], "{{ value }}",
  {% endfor %}
)

{% if not forloop.last %}
#text("")
{% endif %}

{% endfor %}

#line(length: 100%, stroke: mygray)
