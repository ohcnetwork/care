{# templates/reports/typst/header.typ #}

{% if layout.page_numbering.enabled %}
#set page(
  numbering: "{{ layout.page_numbering.format }}",
  number-align: {{ layout.page_numbering.align }}
)
{% endif %}

#set page(
  "{{ layout.page_size }}",
)

{% if layout.page_margin.mode == "uniform" %}
#set page(
  "{{ layout.page_size }}",
  margin: {{ layout.page_margin.value }}
)
{% else %}
#set page(
  "{{ layout.page_size }}",
  margin: (
    top: {{ layout.page_margin.values.top }},
    bottom: {{ layout.page_margin.values.bottom }},
    right: {{ layout.page_margin.values.right }},
    left: {{ layout.page_margin.values.left }}
  )
)
{% endif %}
#set text(font: "DejaVu Sans",size: 10pt,hyphenate: true, fallback: true)

#let mygray = luma(150)

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

#show table: set block(width:100%)
