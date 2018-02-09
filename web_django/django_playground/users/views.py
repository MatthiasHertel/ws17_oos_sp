from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import User
from ..services import moves_service
from ..services import utils_service

import logging
from channels import Channel
import json

import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

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

        print(activity)

        return render(request, 'pages/detail.html', {
            'user': user,
            'activity': activity,
            'date': api_date
        })


class UserActivityMapView(LoginRequiredMixin, View):
    def get(self, request, date, *args, **kwargs):
        api_date = date.replace('-', '')
        user = User.objects.get(username=request.user.username)
        activities = moves_service.get_activities_date(user, utils_service.make_date_from(api_date))

        return render(request, 'pages/map.html', {
            'date': date,
            'activities': activities
        })


class UserActivityGeoJsonView(LoginRequiredMixin, View):
    def get(self, request, date, *args, **kwargs):
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
        return HttpResponse(json.dumps(geojson),  content_type='application/geo+json')


class UserActivityMplView(LoginRequiredMixin, View):
    def get(self, request, date=None, *args, **kwargs):
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
                    plt.plot(x, y, 'o-', color=color_list[act], label=activity)

            except ValueError as err:
                print("Value Error", err)

        # set plot title
        plt.title("Recent Activities")

        # set label x-axis
        plt.xlabel('Date')

        # set label y-axis
        plt.ylabel('Distances (m)')

        # settings for ticks on x-axis
        plt.xticks(fontsize=8, rotation=33)

        # misc settings
        plt.subplots_adjust(bottom=0.15)
        plt.grid(True, 'major', 'x', ls='--', lw=.5, c='k', alpha=.3)

        # enable legend
        plt.legend()

        # prepare the response, setting Content-Type
        response=HttpResponse(content_type='image/svg+xml')
        # print the image on the response
        canvas.print_figure(response, format='svg')
        # and return it
        return response

class UserActivityMplDetailView(LoginRequiredMixin, View):
    def get(self, request, date, index, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        api_date = date.replace('-', '')
        activity = moves_service.get_activity_date(user, utils_service.make_date_from(api_date), int(index))

        print(type(activity))
        print(type(activity['trackPoints']))

        #print(activity)
        speedist = {}

        for tp in activity['trackPoints']:
            for key in tp:
                print(key)
                #print(l['distance'])
            #speedist[tp['speed_kmh']] = tp['distance']

        print(speedist)

        fig = plt.figure()
        canvas = FigureCanvas(fig)
        ax1 = fig.add_subplot(2, 1, 1)
        ax2 = ax1.twiny()
        #plt.box(False)
        #ax1.axis([0, 6, 0, 20])

        #majorLocator = MultipleLocator(10)
        #majorFormatter = FormatStrFormatter('%d')
        #minorLocator = MultipleLocator(5)

        t = np.arange(0.0, 100.0, 0.1)
        s = np.sin(0.1 * np.pi * t) * np.exp(-t * 0.01)

        #ax1.xaxis.set_major_locator(majorLocator)
        #ax1.xaxis.set_major_formatter(majorFormatter)

        # for the minor ticks, use no labels; default NullFormatter
        #ax1.xaxis.set_minor_locator(minorLocator)
        ax1.tick_params(
            axis='x',  # changes apply to the x-axis
            which='minor',  # both major and minor ticks are affected
            bottom='off',  # ticks along the bottom edge are off
            top='on',  # ticks along the top edge are off
            labelbottom='off')  # labels along the bottom edge are off
        #ax2.set_xlim(ax1.get_xlim())

        new_tick_locations = range(100)
        ax2.set_xticks(new_tick_locations, minor=True)
        #ax2.set_xticklabels(tick_function(new_tick_locations))
        #ax2.set_xlabel(r"Modified x-axis: $1/(1+X)$")

        plt.plot(t, s, 'o-')
        # prepare the response, setting Content-Type
        response = HttpResponse(content_type='image/svg+xml')
        # print the image on the response
        canvas.print_figure(response, format='svg')
        # and return it
        return response
