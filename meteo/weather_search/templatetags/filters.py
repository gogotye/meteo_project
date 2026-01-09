from django import template
from django.http import QueryDict

register = template.Library()


@register.filter
def dict_to_querystring(value):
    q = QueryDict('', mutable=True)
    q.update(value)
    q['history'] = 'true'
    return q.urlencode()