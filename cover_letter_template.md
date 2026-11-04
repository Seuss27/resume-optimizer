# {{ contact['Name'] }}

{{ [contact['Location'], contact['Email'], contact['Phone'], contact['LinkedIn']] | select | join(' | ') }}

---

{{ letter_date }}

{% if hiring_manager %}{{ hiring_manager }}

{% endif %}{% if company %}{{ company }}

{% endif %}{% if role %}**Re: {{ role }}**

{% endif %}
Dear {{ hiring_manager or 'Hiring Manager' }},

{{ cover_letter_body }}

Sincerely,

{{ contact['Name'] }}
