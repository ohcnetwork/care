#set box(fill: white, stroke: gray, radius: 4pt, inset: 12pt)

#box[
  #text(12pt, weight: "bold")[Care Team]

  #grid(
    columns: (1fr, 1fr),
    align: (top, left),

    {% for member in care_team %}
      [#text(weight: "semibold")[{{ member.name }}]
       #text(size: 10pt, fill: black)[{{ member.role }}]],
    {% endfor %}
  )
]

#align(center, [#line(length: 40%, stroke: mygray)])
