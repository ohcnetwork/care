#grid(
    columns: (auto, 1fr),
    row-gutter: 1em,
    align: (left, right),
    text(size: 15pt)[= {{ encounter.encounter_class|discharge_summary_display }}],
    grid.cell(align: right, rowspan: 2)[#image("{{ logo_path }}", width: 32%)],
    [#text(fill: mygray, weight: 500)[*Created on {{date}}*]]
)
