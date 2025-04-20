{% load static %}
{% load data_formatting_extras %}
{% load discharge_summary_utils %}

#set page(
  margin: 40pt,
)

#set text(
  size: 10pt,
)

#let mygray = luma(100)

#let frame(stroke) = (x, y) => (
    left: if x > 0 { 0pt } else { stroke },
    right: stroke,
    top: if y < 2 { stroke } else { 0pt },
    bottom: stroke,
)

#set table(
    fill: (_, y) => if calc.odd(y) { rgb("EAF2F5") },
    stroke: frame(rgb("21222C")),
)

{% block content %}{% endblock %}
