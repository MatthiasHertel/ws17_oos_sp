from django import template
from django.contrib.gis.measure import Distance
from datetime import datetime, timedelta

register = template.Library()


@register.filter(name='format_meters')
def format_meters(value, unit):
    if unit == 'km':
        return '{:.2f} km'.format(Distance(m=value).km)

    if unit == 'mi':
        return '{:.2f} miles'.format(Distance(m=value).mi)

    return '{:.2f} meters'.format(Distance(m=value).m)


@register.filter(name='format_miles')
def format_miles(value, unit):
    if unit == 'km':
        return '{:.2f} km'.format(Distance(mi=value).km)

    if unit == 'm':
        return '{:.2f} meters'.format(Distance(mi=value).m)

    return Distance(mi=value).m


@register.filter(name='format_seconds')
def format_seconds(value):
    return '{}'.format(timedelta(seconds=value))


@register.filter(name='format_pizza')
def format_pizza(calories):
    pizza_calories = 900
    return '{} which equals {:.0f} pizzas!'.format(calories, int(calories)/pizza_calories)


@register.filter(name='calories_to_kj')
def calories_to_kj(calories):
    return '{:.0f} kJ'.format(int(calories)*4.184)


@register.filter(name='calories_to_watthour')
def calories_to_watthour(calories):
    return '{:.0f} Wh'.format(int(calories)*1.163)


@register.filter(name='datestring_to_date')
def datestring_to_date(date_string):
    return datetime.strptime(date_string, '%Y%m%dT%H%M%S%z')
