from django.conf.urls import include, url
from channels.routing import route
from .channels.consumers import ws_connect
from .channels.consumers import ws_disconnect
from .channels.consumers import hello
from .channels.consumers import import_data

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
    url(
        regex=r'^moves-data$',
        view=views.UserActivityListView.as_view(),
        name='list'
    ),
    url(
        regex=r'^moves-data/(?P<date>\d{4}\/\d{2})/$',
        view=views.UserActivityMonthView.as_view(),
        name='month'
    ),
    url(
        regex=r'^detail/(?P<date>\d{4}-\d{2}-\d{2})/(?P<index>\d+)/$',
        view=views.UserActivityDetailView.as_view(),
        name='detail'
    ),
    url(
        regex=r'^detail/(?P<date>\d{4}-\d{2}-\d{2})/(?P<index>\d+)/mpl_detail.svg',
        view=views.UserActivityMplDetailView.as_view(), name='mpl_detail'
    ),
    url(
        regex=r'^detail/(?P<date>\d{4}-\d{2}-\d{2})/(?P<index>\d+)/mpl_detail_map.png$',
        view=views.UserActivityDetailMapView.as_view(), name='mpl_detail_map'
    ),
    url(regex=r'^map/(?P<date>\d{4}-\d{2}-\d{2})/$', view=views.UserActivityMapView.as_view(), name='map'),
    url(regex=r'^geojson/(?P<date>\d{4}-\d{2}-\d{2})/$', view=views.UserActivityGeoJsonView.as_view(), name='geojson'),
    url(regex=r'^mpl_recent.svg/(?P<date>\d{4}\d{2})/$', view=views.UserActivityMplView.as_view(), name='mplimage'),
    url(regex=r'^mpl_recent.svg$', view=views.UserActivityMplView.as_view(), name='mpl_recent'),
    url(regex=r'^mpl_pie.svg$', view=views.UserActivityMplPieView.as_view(), name='mpl_pie'),
    url(regex=r'^mpl_pie.svg/(?P<days_to_pie>\d{2})/$', view=views.UserActivityMplPieView.as_view(), name='mpl_pie'),

]

channel_routing = [
    route('background-import-data', import_data),
]
