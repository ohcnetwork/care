{# templates/reports/typst/header.typ #}

#set page(
  numbering: "{{ layout.page_numbering.format }}",
  number-align: {{ layout.page_numbering.align }}
)
#set page(
  "{{ layout.page_size }}",
  margin: {{ layout.page_margin.value }}
)
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

#align(
  {{ header.facility_heading.align }},
  text({{ header.facility_heading.size }}, weight: "{{ header.facility_heading.weight }}")[
    {{ facility_name }}
  ]
)

#line(length: {{ header.divider.length }}, stroke: {{ header.divider.stroke }})

#grid(
    columns: (auto, 1fr),
    row-gutter: 1em,
    align: (left, right),
  text(size: {{ header.title.size }})[
    = {{ header.title.text }}
  ],

  grid.cell(
    align: right,
    rowspan: 2
  )[
      #image("{{ logo_file_name }}",width: 40%)
  ],

  [
    #text(
      fill: {{ header.created_on.style.fill }},
      weight: {{ header.created_on.style.weight }}
    )[
      *{{ header.created_on.label }} #datetime.today().display("{{ header.created_on.date_format }}")*
    ]
  ]
)

#line(length: {{ header.divider.length }}, stroke: {{ header.divider.stroke }})
