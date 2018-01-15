from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

import json
import matplotlib.pyplot as plt

from .models import User
from .models import MovesProfile
from ..services import moves_service


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        user_is_authenticated = moves_service.is_user_authenticated(user)

        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['moves_connected'] = user_is_authenticated
        context['moves_auth_url'] = moves_service.get_auth_url()

        days = []
        if user_is_authenticated:
            moves_service.validate_authentication(user)
            context['data'] = moves_service.get_summary_past_days(user, 30)
            # for day in context['data']:
            #     daily_sum = 0
            #     if day['summary']:
            #         for activity in day['summary']:
            #             if activity['activity'] == 'cycling':
            #                 daily_sum += activity['distance']
            #     days.append(daily_sum)


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


class UserMovesRegisterView(LoginRequiredMixin, SingleObjectMixin, View):
    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if 'code' in request.GET:
            try:
                moves_service.create_auth(request.GET.get('code'), user)
                return redirect('users:detail', username=request.user.username)
            except Exception as e:
                return JsonResponse(e, 400)
        elif 'error' in request.GET:
            return HttpResponse(request.GET, 400)
        else:
            return HttpResponse('Unknown Error', 500)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'
