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


@register.filter(name='format_miles')
def format_miles(value, unit):
    if unit == 'km':
        return '{:.0f} km'.format(Distance(mi=value).km)

    if unit == 'm':
        return '{:.0f} meters'.format(Distance(mi=value).m)

    return Distance(mi=value).m


@register.filter(name='format_seconds')
def format_seconds(value):
    return '{}'.format(datetime.timedelta(seconds=value))


@register.filter(name='format_pizza')
def format_pizza(calories):
    pizza_calories = 900
    return '{} which equals {:.0f} pizzas!'.format(calories, int(calories)/pizza_calories)
