from django import template
from django.contrib.gis.measure import Distance
import datetime

register = template.Library()


@register.filter(name='format_meters')
def format_meters(value, unit):
    if unit == 'km':
        return '{:.0f} km'.format(Distance(m=value).km)

    if unit == 'mi':
        return '{:.0f} miles'.format(Distance(m=value).mi)

    return Distance(m=value).m


@register.filter(name='format_seconds')
def format_seconds(value):
    return '{}'.format(datetime.timedelta(seconds=value))
