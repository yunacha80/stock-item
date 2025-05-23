from django import template

register = template.Library()

@register.filter
def strip_zenkaku_spaces(value):
    if isinstance(value, str):
        return value.replace("　", "").strip()
    return value
