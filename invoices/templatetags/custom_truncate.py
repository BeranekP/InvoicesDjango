from django import template


register = template.Library()


def my_cap(str):
    return str[0].upper()+str[1:]


@register.filter
def custom_truncate(value, to):
    return my_cap(value.replace('Fakturuji Vám za ', ''))
