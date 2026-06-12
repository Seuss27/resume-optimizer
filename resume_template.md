# {{ contact['Name'] }}

**Email:** {{ contact['Email'] }} | **LinkedIn:** {{ contact['LinkedIn'] }}

---

{% if professional_summary %}
{{ professional_summary | wordwrap(100) }}

---
{% endif %}

## Professional Skills

{{ skills_list | join(' • ') }}

## Professional Experience

{% if grouped_layout %}
{% for co in experience %}

### {{ co.company }} | {{ co.dates }}

{% for role in co.roles %}
**{{ role.title }}** | *{{ role.dates }}*

{% for bullet in role.bullets %}

* {{ bullet | wordwrap(98) }}
{% endfor %}
{% endfor %}
{% endfor %}
{% else %}
{% for co in experience %}
{% for role in co.roles %}

### {{ co.company }} — {{ role.title }} | {{ role.dates }}

{% for bullet in role.bullets %}

* {{ bullet | wordwrap(98) }}
{% endfor %}
{% endfor %}
{% endfor %}
{% endif %}
{% if certifications and certifications|length > 0 %}

## Certifications

{% for cert in certifications %}

* {{ cert | wordwrap(98) }}
{% endfor %}
{% endif %}
{% if education and education|length > 0 %}

## Education

{% for edu in education %}

* **{{ edu.degree }}** | {{ edu.institution }}{% if edu.year %}
({{ edu.year }})
{% endif %}
{% endfor %}
{% endif %}
