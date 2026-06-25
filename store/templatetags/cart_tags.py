from django import template

register = template.Library()

@register.simple_tag
def multiply(value, arg):
    """Multiply two values"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply_filter(value, arg):
    """Multiply filter for templates"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtotal(value, arg):
    """Calculate subtotal"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0