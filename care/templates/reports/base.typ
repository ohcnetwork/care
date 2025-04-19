{% load static %}
{% load data_formatting_extras %}
{% load discharge_summary_utils %}

#set page("{{page_size}}",margin: {{page_margin}}pt, {% if numbering %} numbering: "{{numbering_format}}" {% endif %})
#set text(font: "{{font}}",size: {{font_size}}pt,hyphenate: true, fallback: true)
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
