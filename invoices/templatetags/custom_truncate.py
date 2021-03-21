from django import template


register = template.Library()


@register.filter
def custom_truncate(value, to):
    return value.replace('Fakturuji Vám za ', '').capitalize()
