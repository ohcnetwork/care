{% extends "reports/base.typ" %}

{% block content %}

#text(16pt, weight: "bold")[Discharge Summary]

#v(10pt)

{% include "reports/tables.typ" %}

{% endblock %}
