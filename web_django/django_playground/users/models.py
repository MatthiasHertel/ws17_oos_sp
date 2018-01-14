from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField


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
