import os

from django import template


register = template.Library()


@register.filter
def zipcode(value):
    return ' '.join([str(value)[0:3], str(value)[3:]])
