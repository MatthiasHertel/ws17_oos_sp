from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import logging
import requests

from ..users.models import MovesProfile, MovesHistoryDate, MovesHistorySegment, MovesHistorySegmentActivity
from datetime import date, datetime, timedelta
import dateutil.parser

# Get an instance of a logger
logger = logging.getLogger(__name__)


class MovesService:
    """Service that offers Access to MOVES Api - https://dev.moves-app.com ."""

    config = settings.MOVES

    def is_user_authenticated(self, user):
        try:
            return True if user.moves_profile.moves_access_token and user.moves_profile.moves_refresh_token else False
        except ObjectDoesNotExist:
            user.moves_profile = MovesProfile()
            user.moves_profile.save()
            return False

    def get_data(self, data_type, user, **kwargs):
        filters = ''
        date = ''

        if 'date' in kwargs:
            date = '/' + kwargs['date']

        for param in kwargs:
            if param != 'date':
                filters += '{}={}&'.format(param, kwargs[param])

        url = '{}/user/{}/daily{}?{}'.format(self.config['api'], data_type, date, filters)
        r = requests.get(url, headers=self.get_headers(user))
        print('MOVES API Request: {}'.format(url))
        print('MOVES API Response: {}'.format(r.text))
        return r.json()

    def get_activities_past_days(self, user, days_past):
        return self.get_data('activities', user, pastDays=days_past)

    def get_summary_past_days(self, user, days_past):
        return self.get_data('summary', user, pastDays=days_past)

    def get_storyline_past_days(self, user, days_past):
        return self.get_data(data_type='storyline', user=user, pastDays=days_past, trackPoints='true')

    def get_storyline_date(self, user, date):
        return self.get_data(data_type='storyline', user=user, date=date, trackPoints='true')

    def import_storyline_date(self, user, date):
        storyline_data = self.get_data(data_type='storyline', user=user, date=date, trackPoints='true')

        for day in storyline_data:
            moves_history_date = user.moves_history_dates.create(
                date=self.create_date(day['date']),
                data=day['summary']
            )
            for segment in day['segments']:
                # moves_history_date.moves_history_segments.create(
                #     type=segment['type'],
                #     start=segment['startTime'],
                #     end=segment['endTime'],
                #     last_update=segment['lastUpdate']
                # )
                for activity in segment['activities']:
                    pass

    def get_profile(self, user):
        url = '{}/user/profile'.format(self.config['api'])
        r = requests.get(url, headers=self.get_headers(user))
        return r.json()

    def sync_profile_data(self, user):
        profile = self.get_profile(user)
        user.moves_profile.data = profile

    def create_auth(self, code, user):
        """Create first access Token using Smartphone code from callback url."""
        access_token_url = '{}/access_token?grant_type=authorization_code&code={}&client_id={}&client_secret={}'.format(self.config['api_auth'], code, self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            user.moves_profile.moves_access_token = response['access_token']
            user.moves_profile.moves_refresh_token = response['refresh_token']
            self.sync_profile_data(user)
            user.moves_profile.save()
        else:
            raise Exception(response['error'])

    def get_auth_url(self):
        """Generate Auth URL to connect Smartphone App."""
        return '{}/authorize?response_type=code&client_id={}&scope=activity location'.format(self.config['api_auth'], self.config['client_id'])

    def validate_access_token(self, user):
        """Validate the access token."""
        validate_url = '{}/tokeninfo?access_token={}'.format(self.config['api_auth'], user.moves_profile.moves_access_token)
        response = requests.get(validate_url).json()
        return True if 'error' not in response else False

    def refresh_access_token(self, user):
        """Refresh the access token."""
        access_token_url = '{}/access_token?grant_type=refresh_token&refresh_token={}&client_id={}&client_secret={}'.format(self.config['api_auth'], user.moves_profile.moves_refresh_token, self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            user.moves_profile.moves_access_token = response['access_token']
            user.moves_profile.moves_refresh_token = response['refresh_token']
            self.sync_profile_data(user)
            user.moves_profile.save()
        else:
            raise Exception(response['error'])

    def validate_authentication(self, user):
        """Check if user has a valid access token and if not refresh it."""
        if not self.validate_access_token(user):
            self.refresh_access_token(user)

    def get_config(self):
        return settings.MOVES

    def get_headers(self, user):
        return {'Authorization':  'Bearer {}'.format(user.moves_profile.moves_access_token)}

    def create_date(self, yyyymmdd):
        # year = int(str(yyyymmdd)[0:4])
        # month = int(str(yyyymmdd)[4:6])
        # day = int(str(yyyymmdd)[6:8])
        #
        # return date(year, month, day)

        return dateutil.parser.parse(yyyymmdd)
