# {{ contact['Name'] }}
**Email:** {{ contact['Email'] }} | **LinkedIn:** {{ contact['LinkedIn'] }}

---
{% if professional_summary %}
{{ professional_summary }}

---
{% endif %}
## Professional Skills
{{ skills_list | join(' • ') }}

## Professional Experience

{% for role in experience %}
### {{ role.title }} | {{ role.company }}
*{{ role.dates }}*

{% for bullet in role.bullets %}
* {{ bullet }}
{% endfor %}

{% endfor %}

{% if certifications and certifications|length > 0 %}
## Certifications
{% for cert in certifications %}
* {{ cert }}
{% endfor %}
{% endif %}

{% if education and education|length > 0 %}
## Education
{% for edu in education %}
* **{{ edu.degree }}** | {{ edu.institution }}{% if edu.year %} ({{ edu.year }}){% endif %}
{% endfor %}
{% endif %}