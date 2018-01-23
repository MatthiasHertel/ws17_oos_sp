from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import logging
import requests

from ..users.models import DataProfile, DataPoint
from datetime import datetime, timedelta

# Get an instance of a logger
logger = logging.getLogger(__name__)


class MovesService:
    """Service that offers Access to MOVES Api - https://dev.moves-app.com ."""

    config = settings.MOVES

    name = 'moves'

    def is_user_authenticated(self, user):
        try:
            moves_profile = user.data_profiles.get(provider=self.name)
            if 'access_token' in moves_profile.auth_data and moves_profile.auth_data['access_token'] and 'refresh_token' in moves_profile.auth_data and moves_profile.auth_data['refresh_token']:
                return True
            else:
                return False
        except ObjectDoesNotExist:
            user.data_profiles.create(
                provider=self.name
            )
            return False

    def get_data(self, data_type, moves_profile, **kwargs):
        filters = ''
        date = ''

        if 'date' in kwargs:
            date = '/' + kwargs['date'].strftime('%Y%m%d')

        for param in kwargs:
            if param != 'date':
                filters += '{}={}&'.format(param, kwargs[param])

        url = '{}/user/{}/daily{}?{}'.format(self.config['api'], data_type, date, filters)
        print(url)
        r = requests.get(url, headers=self.get_headers(moves_profile))
        print('MOVES API Request: {}'.format(url))
        print('MOVES API Response: {}'.format(r.text))
        return r.json()

    def get_activities_past_days(self, user, days_past):
        return self.get_data('activities', user.data_profiles.get(provider=self.name), pastDays=days_past)

    def get_summary_past_days(self, user, days_past):
        return self.get_data('summary', user.data_profiles.get(provider=self.name), pastDays=days_past)

    def get_storyline_past_days(self, user, days_past):
        return self.get_data(data_type='storyline', moves_profile=user.data_profiles.get(provider=self.name), pastDays=days_past, trackPoints='true')

    def get_storyline_date(self, user, date):
        return self.get_data(data_type='storyline', moves_profile=user.data_profiles.get(provider=self.name), date=date, trackPoints='true')

    def import_storyline(self, user):
        moves_profile = user.data_profiles.get(provider=self.name)
        if 'profile' in moves_profile.data:
            next_date = self.create_date(moves_profile.data['profile']['firstDate'])
            current_date = datetime.now() + timedelta(days=1)
            import_done = False
            while not import_done:
                self.import_storyline_date(user, next_date)
                next_date = next_date + timedelta(days=1)
                if next_date.strftime('%Y%m%d') == current_date.strftime('%Y%m%d'):
                    import_done = True

    def import_storyline_date(self, user, date):
        moves_profile = user.data_profiles.get(provider=self.name)
        storyline_data = self.get_data(data_type='storyline', moves_profile=moves_profile, date=date, trackPoints='true')

        for day in storyline_data:
            if 'segments' in day and day['segments']:
                for segment in day['segments']:
                    if not moves_profile.data_points.filter(
                        date=self.create_date(day['date']),
                        type=segment['type'],
                        data__lastUpdate__contains=segment['lastUpdate']
                    ):
                        moves_profile.data_points.create(
                            date=self.create_date(day['date']),
                            type=segment['type'],
                            data=segment
                        ).save()

    def get_profile(self, moves_profile):
        url = '{}/user/profile'.format(self.config['api'])
        r = requests.get(url, headers=self.get_headers(moves_profile))
        return r.json()

    def sync_profile_data(self, moves_profile):
        profile = self.get_profile(moves_profile)
        moves_profile.data = profile

    def create_auth(self, code, user):
        """Create first access Token using Smartphone code from callback url."""
        access_token_url = '{}/access_token?grant_type=authorization_code&code={}&client_id={}&client_secret={}'.format(self.config['api_auth'], code, self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            moves_profile = user.data_profiles.get(provider=self.name)
            moves_profile.auth_data = response
            self.sync_profile_data(moves_profile)
            moves_profile.save()
        else:
            raise Exception(response['error'])

    def get_auth_url(self):
        """Generate Auth URL to connect Smartphone App."""
        return '{}/authorize?response_type=code&client_id={}&scope=activity location'.format(self.config['api_auth'], self.config['client_id'])

    def validate_access_token(self, user):
        """Validate the access token."""
        moves_profile = user.data_profiles.get(provider=self.name)
        validate_url = '{}/tokeninfo?access_token={}'.format(
            self.config['api_auth'], moves_profile.auth_data['access_token']
        )
        response = requests.get(validate_url).json()
        return True if 'error' not in response else False

    def refresh_access_token(self, user):
        """Refresh the access token."""
        moves_profile = user.data_profiles.get(provider=self.name)
        access_token_url = '{}/access_token?grant_type=refresh_token&refresh_token={}&client_id={}&client_secret={}'.format(self.config['api_auth'], moves_profile.auth_data['refresh_token'], self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            moves_profile.auth_data = response
            self.sync_profile_data(user)
            moves_profile.save()
        else:
            raise Exception(response['error'])

    def validate_authentication(self, user):
        """Check if user has a valid access token and if not refresh it."""
        if not self.validate_access_token(user):
            self.refresh_access_token(user)

    def get_config(self):
        return settings.MOVES

    def get_headers(self, moves_profile):
        return {'Authorization':  'Bearer {}'.format(moves_profile.auth_data['access_token'])}

    def create_date(self, date_string):
        try:
            return datetime.strptime(date_string, '%Y%m%dT%H%M%S%z')
        except ValueError:
            return datetime.strptime(date_string, '%Y%m%d')
