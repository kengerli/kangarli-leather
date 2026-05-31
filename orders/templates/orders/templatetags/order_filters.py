from django import template
import datetime

register = template.Library()

@register.filter(name='add_days')
def add_days(value, days):
    try:
        return value + datetime.timedelta(days=int(days))
    except:
        return value