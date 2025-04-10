from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    Splits a string into a list on arg
    Usage: {{ value|split:"," }}
    """
    return value.split(arg)

@register.filter
def strip(value):
    """
    Strips whitespace from a string
    Usage: {{ value|strip }}
    """
    return value.strip()