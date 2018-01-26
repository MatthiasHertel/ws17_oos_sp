from django.conf.urls import url
from channels.routing import route
from .channels.consumers import ws_message

from . import views

urlpatterns = [
    url(
        regex=r'^$',
        view=views.UserListView.as_view(),
        name='list'
    ),
    url(
        regex=r'^~redirect/$',
        view=views.UserRedirectView.as_view(),
        name='redirect'
    ),
    url(
        regex=r'^(?P<username>[\w.@+-]+)/$',
        view=views.UserDetailView.as_view(),
        name='detail'
    ),
    url(
        regex=r'^~update/$',
        view=views.UserUpdateView.as_view(),
        name='update'
    ),
    url(
        regex=r'^~moves/register$',
        view=views.UserMovesRegisterView.as_view(),
        name='moves_register'
    ),
    url(
        regex=r'^~moves/import$',
        view=views.UserMovesImportView.as_view(),
        name='moves_import'
    ),
    url('list', views.list, name='list'),
    url(
        regex=r'^month/(?P<date>\d{4}\d{2})/$',
        view=views.month,
        name='month'
    ),
    url(regex=r'^map/(?P<date>\d{4}-\d{2}-\d{2})/$', view=views.map, name='map'),
    url(regex=r'^geojson/(?P<date>\d{4}-\d{2}-\d{2})/$', view=views.geojson, name='geojson'),
]

channel_routing = [
    # route("http.request", "django_playground.users.views.http_consumer"),
    route("websocket.receive", ws_message)
]
