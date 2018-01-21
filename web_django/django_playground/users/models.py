from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField

import datetime


@python_2_unicode_compatible
class User(AbstractUser):

    name = models.CharField(_('Name of User'), blank=True, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})


class DataProfile(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='data_profiles'
    )

    provider = models.CharField(_('Name of Data Provider'), editable=False, max_length=255)
    auth_data = JSONField(default=dict)
    data = JSONField(default=dict)

    def __str__(self):
        return "Data Profile of User {}".format(self.user.name)


class DataPoint(models.Model):
    data_profile = models.ForeignKey(
        DataProfile,
        on_delete=models.CASCADE,
        related_name='data_points'
    )
    date = models.DateField(_('Date for the Data Point'), editable=False, default=datetime.date.today)
    type = models.CharField(_('Type of Data Point'), editable=False, max_length=255)
    data = JSONField(default=dict)

    def __str__(self):
        return "Data Point for a specific data provider and date {}".format(self.user.name)
