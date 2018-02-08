from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import User
from .models import DataProfile
from ..services import moves_service
from ..services import utils_service

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

import logging
logger = logging.getLogger(__name__)
import requests
from channels import Channel
import json

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        # TODO why not the whole user object ?
        username = User.objects.get(username=self.request.user.username)
        user_is_authenticated = moves_service.is_user_authenticated(username)

        if user_is_authenticated:
            moves_service.validate_authentication(username)
        user = self.request.user

        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['moves_connected'] = user_is_authenticated
        context['moves_auth_url'] = moves_service.get_auth_url()
        context['moves_data_available'] = moves_service.moves_data_available(user)

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
                # moves_service.import_storyline(user)
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


class UserActivityListView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        utils_service.hello()
        user = User.objects.get(username=request.user.username)
        summary = moves_service.get_summary_past_days(user, 30)

        for day in summary:
            day['dateObj'] = utils_service.make_date_from(day['date'])
            day['summary'] = utils_service.make_summaries(day)

        moves_profile = user.data_profiles.get(provider='moves')
        using_for = utils_service.get_days_using(moves_profile.data['profile']['firstDate'])
        months = utils_service.get_month_range(moves_profile.data['profile']['firstDate'])

        return render(request, 'pages/list.html', {
            'user': user,
            # 'profile': json.dumps(moves_profile.data, indent=2),
            'profile': moves_profile.data,
            'summary': summary,
            'days': using_for,
            'months': months
        })


class UserActivityMonthView(LoginRequiredMixin, View):
    """return the rendered month template"""
    def get(self, request, date, *args, **kwargs):
        user = User.objects.get(username=request.user.username)

        # cleanup date first
        date = date.replace('/','')

        # get selected month-name & year for month-view
        selMonth = utils_service.get_month_name(date)
        selYear = utils_service.get_year_name(date)

        summary = moves_service.get_summary_month(user, utils_service.make_date_from(date))
        summary.reverse()
        for day in summary:
            day['dateObj'] = utils_service.make_date_from(day['date'])
            day['summary'] = utils_service.make_summaries(day)

        moves_profile = user.data_profiles.get(provider='moves')
        months = utils_service.get_month_range(moves_profile.data['profile']['firstDate'])

        return render(request, 'pages/month.html', {
            'user': user,
            'profile': json.dumps(moves_profile.data, indent=2),
            'summary': summary,
            'months': months,
            'date' : date,
            'sel_month': selMonth,
            'sel_year' : selYear
        })


class UserActivityDetailView(LoginRequiredMixin, View):
    def get(self, request, date, index, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        api_date = date.replace('-', '')
        activity = moves_service.get_activity_date(user, utils_service.make_date_from(api_date), int(index))
        return render(request, 'pages/detail.html', {
            'user': user,
            'activity': activity
        })

def map(request, date):
    api_date = date.replace('-', '')
    user = User.objects.get(username=request.user.username)
    activities = moves_service.get_activities_date(user, utils_service.make_date_from(api_date))

    return render(request, 'pages/map.html', {
        'date': date,
        'activities': activities
    })


def geojson(request, date):
    """returns a json for mapview is called via ajax in map template"""
    api_date = date.replace('-', '')
    utils_service.validate_date(api_date)

    user = User.objects.get(username=request.user.username)
    info = moves_service.get_storyline_date(user, utils_service.make_date_from(api_date))

    features = []
    for segment in info[0]['segments']:
        if segment['type'] == 'place':
            features.append(utils_service.geojson_place(segment))
        elif segment['type'] == 'move':
            features.extend(utils_service.geojson_move(segment))

    geojson = {'type': 'FeatureCollection', 'features': features}
    filename = "moves-%s.geojson" % date
    # headers = (('Content-Disposition', 'attachment; filename="%s"' % filename),)
    return HttpResponse(json.dumps(geojson),  content_type='application/geo+json')


def mpl_recent(request, date=None):
    """returns a matplot image"""
    # init figure & canvas
    fig = plt.figure()
    canvas = FigureCanvas(fig)


    # color map for coloring diagram-stuff
    # ref: https://matplotlib.org/examples/color/colormaps_reference.html
    color_list = plt.cm.tab10(np.linspace(0, 1, 12))

    user = User.objects.get(username=request.user.username)
    if date is not None:
        adjust_date = utils_service.make_date_from(date)
        summary = moves_service.get_summary_month(user, adjust_date)
    else:
        summary = moves_service.get_summary_past_days(user, 30)

    summary.reverse()
    #print(summary)
    activities = { 1: 'walking', 2: 'run', 3: 'cycling' }

    for act in activities:
        x = []
        y = []
        dailydist = {}
        dailydist.clear()

        activity = activities[act]

        for day in summary:

            if not day['summary']:
                dailydist[day['date']] = 0
                continue
            for element in day['summary']:
                if element['activity'] == activity:
                    dailydist[day['date']] = element['distance']

        try:
            list = sorted(dailydist.items())
            x, y = zip(*list)
            x = [utils_service.make_date_from(key) for key in x]
            #x = [str(key) for key in x]

            # do the plotting
            if np.sum(y) > 0:
                plt.plot(x, y, color=color_list[act], label=activity)

        except ValueError as err:
            print("Value Error", err)


    plt.title("Recent Activities")
    plt.ylabel('Distances (m)')
    plt.xlabel('Date')

    plt.xticks(fontsize=8, rotation=33)
    plt.subplots_adjust(bottom=0.15)
    plt.grid(True, 'major', 'x', ls='--', lw=.5, c='k', alpha=.3)

    plt.legend()

    # prepare the response, setting Content-Type
    response=HttpResponse(content_type='image/svg+xml')
    # print the image on the response
    canvas.print_figure(response, format='svg')
    # and return it
    return response
