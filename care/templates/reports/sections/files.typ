#align(left, text(18pt,)[== Annexes])
#align(left, text(14pt,weight: "bold",)[=== Uploaded Files:])

#table(
    columns: (1fr, 1fr,),
    inset: 10pt,
    align: horizon,
    table.header(
        [*UPLOADED AT*], [*NAME*],
    ),
    {% for file in files %}
        "{{file.modified_date }}", text(hyphenate: true)["{{file.name }}"],
    {% endfor %}
)
