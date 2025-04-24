{# templates/typst/sections/text.typ #}
{% comment %}
  Renders a single-paragraph text block under a level-1 heading.
  Expects in context:
    - title: String
    - text:  String
{% endcomment %}

= {{ title }}

#text()[```{{ text }}```]

#line(length: 100%, stroke: mygray)
