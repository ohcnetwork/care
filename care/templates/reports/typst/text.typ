{% comment %}
  Renders multiple values under a common title.
  Expects in context:
    - title: String
    - text:  List of strings
{% endcomment %}

= {{ title }}

#list(
  {% for t in text %}
    [{{ t }}],
  {% endfor %}
)

#line(length: 100%, stroke: mygray)
