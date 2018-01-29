from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

import json
import matplotlib.pyplot as plt

from .models import User
from .models import DataProfile
from ..services import moves_service

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


import logging
logger = logging.getLogger(__name__)
import requests
from channels import Group, Channel
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        user_is_authenticated = moves_service.is_user_authenticated(user)

        if user_is_authenticated:
            moves_service.validate_authentication(user)

        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['moves_connected'] = user_is_authenticated
        context['moves_auth_url'] = moves_service.get_auth_url()

        # fig = plt.plot(days)
        # plt.ylabel('some numbers')

        return context


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})


class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', ]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})

    def get_object(self):
        # Only get the User record for the user making the request
        return User.objects.get(username=self.request.user.username)


@method_decorator(csrf_exempt, name='dispatch')
class UserMessageView(View):
    def post(self, request):
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        Group('user_{}'.format(body.user_id)).send({
            'text': json.dumps({
                'message': 'Shitty'
            })
        })

        return JsonResponse(dict())


class UserMovesRegisterView(LoginRequiredMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if 'code' in request.GET:
            try:
                moves_service.create_auth(request.GET.get('code'), user)
                return redirect('users:detail', username=request.user.username)
            except Exception as e:
                return JsonResponse(e.msg, 400)
        elif 'error' in request.GET:
            return HttpResponse(request.GET, 400)
        else:
            return HttpResponse('Unknown Error', 500)


class UserMovesImportView(LoginRequiredMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if moves_service.is_user_authenticated(user):
            try:
                Channel('background-import-data').send(dict(
                    provider='moves',
                    user_id=user.id
                ))
                return redirect('users:detail', username=user.username)
            except Exception as e:
                return HttpResponse(e.msg, 400)
        else:
            return HttpResponse('Moves Not Authenticated', 400)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'


def map(request, date):

    return render(request, 'pages/map.html', {
        'date':date
        })


def list(request):

    user = User.objects.get(username=request.user.username)

    summary = moves_service.get_summary_past_days(user, 30)

    for day in summary:
        day['dateObj'] = make_date_from(day['date'])
        day['summary'] = make_summaries(day)

    moves_profile = user.data_profiles.get(provider='moves')
    using_for = get_days_using(moves_profile.data['profile']['firstDate'])
    months = get_month_range(moves_profile.data['profile']['firstDate'])

    return render(request, 'pages/list.html', {
            'user': user,
            'profile': json.dumps(moves_profile.data, indent=2),
            'summary': summary,
            'days': using_for,
            'months': months
    })


def geojson(request, date):
    api_date = date.replace('-', '')
    validate_date(api_date)

    user = User.objects.get(username=request.user.username)
    info = moves_service.get_storyline_date(user, make_date_from(api_date))

    features = []
    for segment in info[0]['segments']:
        if segment['type'] == 'place':
            features.append(geojson_place(segment))
        elif segment['type'] == 'move':
            features.extend(geojson_move(segment))

    geojson = {'type': 'FeatureCollection', 'features': features}
    filename = "moves-%s.geojson" % date
    # headers = (('Content-Disposition', 'attachment; filename="%s"' % filename),)
    return HttpResponse(json.dumps(geojson),  content_type='application/geo+json')


def month(request, date):

    user = User.objects.get(username=request.user.username)

    # get selected month-name & year for month-view
    selMonth = get_month_name(date)
    selYear = get_year_name(date)

    summary = moves_service.get_summary_month(user, make_date_from(date))
    summary.reverse()
    for day in summary:
        day['dateObj'] = make_date_from(day['date'])
        day['summary'] = make_summaries(day)

    moves_profile = user.data_profiles.get(provider='moves')
    months = get_month_range(moves_profile.data['profile']['firstDate'])

    return render(request, 'pages/month.html', {
            'user': user,
            'profile': json.dumps(moves_profile.data, indent=2),
            'summary': summary,
            'months': months,
            'date' : date,
            'sel_month': selMonth,
            'sel_year' : selYear
    })


def validate_date(date):
    date = date.replace('-', '')
    try:
        date_obj = make_date_from(date)
    except Exception as e:
        raise Exception("Date is not in the valid format: %s" % e)


def get_month_range(first_date, last_date=None, excluding=None):
    months = []

    first = make_date_from(first_date)
    if last_date:
        cursor = make_date_from(last_date)
    else:
        cursor = datetime.utcnow().date()

    if excluding:
        (x_year, x_month) = excluding.split('-')
    else:
        x_year = x_month = "0"

    while cursor.year > first.year or cursor.month >= first.month and cursor.year >= 2010:
        if not(cursor.year == int(x_year) and cursor.month == int(x_month)):
            months.append(cursor)
        # logger.info("have cursor %s, first %s - moving back by 1 month" % (cursor, first))
        cursor = cursor - relativedelta(months=1)

    return months


def get_dates_range(first_date):
    first = make_date_from(first_date)

    cursor = datetime.utcnow().date() # TODO use profile TZ?
    days = []

    # there is something badly wrong here
    while cursor >= first:
        days.append(cursor)
        cursor = cursor - timedelta(days=1)

    return days

def get_days_using(first_date):
    first = make_date_from(first_date)
    now = datetime.utcnow().date()

    delta = now-first
    return delta.days


def make_date_from(yyyymmdd):
    yyyymmdd = yyyymmdd.replace('-', '')

    year = int(str(yyyymmdd)[0:4])
    month = int(str(yyyymmdd)[4:6])
    try:
        day = int(str(yyyymmdd)[6:8])
    except:
        day = 1

    re = date(year, month, day)
    return re

def get_month_name(yyyymm):
    month = int(str(yyyymm)[4:6])
    # generating month name from month int
    mstr = date(1900, month, 1).strftime('%B')
    return mstr


def get_year_name(yyyymm):
    year = int(str(yyyymm)[0:4])
    return str(year)


def make_summaries(day):
    returned = {}
    lookup = {'walking': 'walking', 'run': 'ran', 'cycling': 'cycled', 'transport': 'Transport'}

    if not day['summary']:
        return {'walking': 'No activity'}

    for summary in day['summary']:
        returned[summary['activity']] = make_summary(summary, lookup)

    return returned


def make_summary(object, lookup):
    return "%s for %.1f km, taking %i minutes" % (lookup[object['activity']],
            float(object['distance'])/1000, float(object['duration'])/60)


def geojson_place(segment):
    feature = {'type': 'Feature', 'geometry': {}, 'properties': {}}

    coordinates = [segment['place']['location']['lon'], segment['place']['location']['lat']]
    feature['geometry'] = {"type": "Point", "coordinates": coordinates}

    for key in segment.keys():
        # TODO convert activity?
        feature['properties'][key] = segment[key]

    # make a nice duration number as well
    # print(segment['startTime'])
    # start = datetime.strptime(segment['startTime'], '%Y%m%dT%H%M%Sz')
    # end = datetime.strptime(segment['endTime'], '%Y%m%dT%H%M%Sz')
    # duration = end-start
    # feature['properties']['duration'] = duration.seconds

    # name and description
    if 'name' in segment['place']:
        feature['properties']['title'] = segment['place']['name']
    else:
        feature['properties']['title'] = "Unknown"

    if 'foursquareId' in segment['place']:
        feature['properties']['url'] = "https://foursquare.com/v/"+segment['place']['foursquareId']

    # styling
    feature['properties']['icon'] = {
        "iconUrl": "/static/images/circle-stroked-24.svg",
        "iconSize": [24, 24],
        "iconAnchor": [12, 12],
        "popupAnchor": [0, -12]
    }

    return feature


def geojson_move(segment):
    features = []
    lookup = {'walking': 'Walking', 'transport': 'Transport', 'run': 'Running', 'cycling': 'Cycling'}
    stroke = {'walking': '#00d45a', 'transport': '#000000', 'run': '#93139a', 'cycling': '#00ceef'}
    # print ("\n\n\n\n\n\n\n\n\n\n\{}".format(segment))
    for activity in segment['activities']:
        trackpoints = activity['trackPoints']
        coordinates = [[point['lon'], point['lat']] for point in trackpoints]
        timestamps = [point['time'] for point in trackpoints]
        geojson = {'type': 'Feature', 'geometry': {}, 'properties': {}}
        geojson['geometry'] = {'type': 'LineString', 'coordinates': coordinates}
        for key in activity.keys():
            if key != 'trackPoints':
                geojson['properties'][key] = activity[key]

        # add a description & the saved timestamps
        geojson['properties']['description'] = make_summary(activity, lookup)
        geojson['properties']['times'] = timestamps

        # add styling
        geojson['properties']['stroke'] = stroke[activity['activity']]
        geojson['properties']['stroke-width'] = 3
        if activity['activity'] == 'trp':
            geojson['properties']['stroke-opacity'] = 0.1

        features.append(geojson)

    return features
