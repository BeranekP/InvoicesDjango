import os

from django import template


register = template.Library()


@register.filter
def custom_truncate(value, to):
    words = value.strip('.').strip(' ').split()

    return ' '.join(words[3:to])
