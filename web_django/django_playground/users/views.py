from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect

from django.contrib.auth.mixins import LoginRequiredMixin

import requests

from .models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'


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
            access_token_url = '{}/access_token?grant_type=authorization_code&code={}&client_id={}&client_secret={}'.format(settings.MOVES['api_auth'], request.GET.get('code'), settings.MOVES['client_id'], settings.MOVES['client_secret'])
            r = requests.post(access_token_url)
            json_r = r.json()
            if 'error' not in json_r:
                user.moves_access_token = json_r['access_token']
                user.save()
                return redirect('users:detail', username=request.user.username)
            else:
                return JsonResponse(json_r, 400)
        elif 'error' in request.GET:
            return HttpResponse(request.GET, 400)
        else:
            return HttpResponse('Unknown Error', 500)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'
