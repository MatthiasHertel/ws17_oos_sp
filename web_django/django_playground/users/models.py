from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField
import datetime


@python_2_unicode_compatible
class User(AbstractUser):

    name = models.CharField(_('Name of User'), blank=True, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})


class MovesProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='moves_profile'
    )

    moves_access_token = models.CharField(_('Moves API Access Token of User'), blank=True, max_length=255)
    moves_refresh_token = models.CharField(_('Moves API Refresh Token of User'), blank=True, max_length=255)
    data = JSONField(default=list)

    def __str__(self):
        return "Moves Profile of User {}".format(self.user.name)


class MovesHistoryDate(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='moves_history_dates'
    )
    date = models.DateField(_('Date for the History Data'), editable=False, default=datetime.date.today)
    data = JSONField(default=list)

    def __str__(self):
        return "Moves Data History of User {}".format(self.user.name)


class MovesHistorySegment(models.Model):
    moves_history_date = models.ForeignKey(
        MovesHistoryDate,
        on_delete=models.CASCADE,
        related_name='moves_history_segments'
    )

    type = models.CharField(_('Type of Segment'),editable=False, max_length=255)
    start = models.DateTimeField(_('Start of Segment'), editable=False, default=datetime.date.today)
    end = models.DateTimeField(_('End of Segment'), editable=False, default=datetime.date.today)
    last_update = models.DateTimeField(_('Last Update to Segment'), editable=False, default=datetime.date.today)
    data = JSONField(default=list)

    def __str__(self):
        return "Moves Segment of a MovesHistoryDate {}".format(self.moves_history_date.date)


class MovesHistorySegmentActivity(models.Model):
    moves_history_segment = models.ForeignKey(
        MovesHistorySegment,
        on_delete=models.CASCADE,
        related_name='moves_history_activities'
    )

    activity = models.CharField(_('Type of Activity'),editable=False, max_length=255)
    group = models.CharField(_('Group of Activity'),editable=False, max_length=255)
    duration = models.IntegerField(_('Duration of Activity'),editable=False)
    distance = models.IntegerField(_('Distance traveled'),editable=False)
    steps = models.IntegerField(_('Steps taken'),editable=False)
    calories = models.IntegerField(_('Calories burned'),editable=False)
    start = models.DateTimeField(_('Start of Activity'), editable=False, default=datetime.date.today)
    end = models.DateTimeField(_('End of Activity'), editable=False, default=datetime.date.today)
    trackpoints = JSONField(_('LatLong Trackpoints'),default=list)

    def __str__(self):
        return "Moves Activity of a Segment {}".format(self.moves_history_date.date)
