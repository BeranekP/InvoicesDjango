import os

from django import template


register = template.Library()


@register.filter
def custom_truncate(value, to):
    return value[17:17+to]
