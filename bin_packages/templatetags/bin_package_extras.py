from django import template


register = template.Library()


@register.filter
def dict_get(value, arg):
    """Access a dictionary by key, return empty string if the key does not exists."""
    return value.get(arg, '')
