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