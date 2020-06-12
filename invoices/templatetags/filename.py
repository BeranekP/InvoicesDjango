import os

from django import template


register = template.Library()


@register.filter
def filename(value):
    name = os.path.basename(value)
    parent = os.path.basename(os.path.dirname(value))
    topmost = os.path.basename(os.path.dirname(os.path.dirname(value)))
    return os.path.join(topmost, parent, name)
