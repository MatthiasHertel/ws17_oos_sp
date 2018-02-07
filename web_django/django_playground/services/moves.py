from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import logging
import requests

import json
import sys
import math
from datetime import datetime, timedelta
from operator import itemgetter, attrgetter
from calendar import monthrange

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
    def moves_data_available(self, user):
        """Simple Check if any moves-data already exists (depend on the view data functionality)"""
        moves_profile = user.data_profiles.get(provider=self.name)
        return moves_profile.data_points.exists()

    def get_data(self, data_type, moves_profile, **kwargs):
        filters = ''
        date = ''

        if 'date' in kwargs:
            date = '/' + kwargs['date'].strftime('%Y%m%d')

        for param in kwargs:
            if param != 'date':
                filters += '{}={}&'.format(param, kwargs[param])

        url = '{}/user/{}/daily{}?{}'.format(self.config['api'], data_type, date, filters)
        print('MOVES API Request: {}'.format(url))
        r = None
        try:
            r = requests.get(url, headers=self.get_headers(moves_profile))
        except Exception as e:
            raise Exception('MOVES API ERROR: {}'.format(r.text))

        try:
            # print('MOVES API Response: {}'.format(r.text))
            return r.json()
        except ValueError:
            raise ValueError('MOVES API Response did not contain JSON: {}'.format(r.text))

    def get_data_points_month(self, user, date):
        first_dat, num_days = monthrange(date.year, date.month)
        moves_profile = user.data_profiles.get(provider=self.name)
        to_date = date + timedelta(days=num_days)
        data_points = moves_profile.data_points.filter(
            date__gte=date,
            date__lte=to_date
        )
        return self.transform_data_points(data_points)

    def get_data_points_date(self, user, date):
        moves_profile = user.data_profiles.get(provider=self.name)
        data_points = moves_profile.data_points.filter(
            date=date
        )
        return self.transform_data_points(data_points)

    def get_data_points_past_days(self, user, days_past):
        moves_profile = user.data_profiles.get(provider=self.name)
        to_date = moves_profile.data_points.latest('date').date
        from_date = to_date - timedelta(days=days_past)
        data_points = moves_profile.data_points.filter(
            date__gte=from_date,
            date__lte=to_date
        ).order_by('date')
        # TODO die ausgabe ist nicht deterministisch heisst das order by oben ist nutzlos durch den aufruf von transform_data_points
        return self.transform_data_points(data_points)

    def transform_data_points(self, data_points):
        data_by_day = dict()
        for p in data_points:
            if p.date not in data_by_day:
                data_by_day[p.date] = dict(
                    date=p.date.strftime('%Y%m%d'),
                    segments=[]
                )

            if p.type == 'move':
                p.data = self.calculate_distances(p.data)

            data_by_day[p.date]['segments'].append(p.data)

        response = []
        for day in data_by_day:
            data_by_day[day]['summary'] = self.calculate_summary(data_by_day[day]['segments'])
            response.append(data_by_day[day])
        return sorted(response, key=itemgetter("date"), reverse=True)

    def calculate_distances(self, data_point):
        # Haversine formula:a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
        # c = 2 ⋅ atan2( √a, √(1−a) )
        # d = R ⋅ c
        # where	φ is latitude, λ is longitude, R is earth’s radius (mean radius = 6,371km);
        # note that angles need to be in radians to pass to trig functions!
        R = 6371e3
        if 'activities' in data_point:
            for activity in data_point['activities']:
                if 'trackPoints' in activity:
                    lastLat = None
                    lastLon = None
                    lastTime = None

                    for track_point in activity['trackPoints']:
                        if not lastLat and not lastLon:
                            lastLat = track_point['lat']
                            lastLon = track_point['lon']
                            lastTime = self.create_date(track_point['time'])
                        else:
                            currentLat = track_point['lat']
                            currentLon = track_point['lon']
                            currentTime = self.create_date(track_point['time'])
                            lat1Radians = math.radians(lastLat)
                            lat2Radians = math.radians(currentLat)
                            latDistance = math.radians(currentLat-lastLat)
                            lonDistance = math.radians(currentLon-lastLon)

                            a = math.sin(latDistance/2) * math.sin(latDistance/2) + math.cos(lat1Radians) * math.cos(lat2Radians) * math.sin(lonDistance/2) * math.sin(lonDistance/2)
                            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                            d = R * c

                            seconds = (currentTime-lastTime).total_seconds()
                            if seconds > 0:
                                meters_per_second= d/seconds
                                meters_per_hour = meters_per_second*60*60
                                km_per_hour = meters_per_hour / 1000
                                track_point['speed'] = meters_per_second
                                track_point['speed_kmh'] = km_per_hour
                                track_point['distance'] = d

                            lastLat = currentLat
                            lastLon = currentLon
                            lastTime = currentTime
        return data_point

    def calculate_summary(self, segments):
        summary = {}
        for segment in segments:
            if 'activities' in segment:
                for activity in segment['activities']:
                    if activity['activity'] not in summary:
                        summary[activity['activity']] = dict(
                            activity=activity['activity'],
                            group=activity['group'],
                            duration=activity['duration'],
                            distance=activity['distance']
                        )
                        if 'steps' in activity:
                            summary[activity['activity']]['steps'] = activity['steps']
                    else:
                        summary[activity['activity']]['duration'] += activity['duration']
                        summary[activity['activity']]['distance'] += activity['distance']
                        if 'steps' in activity:
                            summary[activity['activity']]['steps'] += activity['steps']

        response = []
        for activity_name in summary:
            response.append(summary[activity_name])
        return response

    def get_summary_past_days(self, user, days_past):
        return self.get_data_points_past_days(user, days_past=days_past)

    def get_summary_month(self, user, month_as_date):
        return self.get_data_points_month(user, date=month_as_date)

    def get_storyline_date(self, user, date):
        return self.get_data_points_date(user, date)

    def import_storyline(self, user):
        moves_profile = user.data_profiles.get(provider=self.name)
        if 'profile' in moves_profile.data:
            if moves_profile.data_points.exists():
                next_date = moves_profile.data_points.latest('date').date - timedelta(days=1)
            else:
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
        try:
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
                            )
        except Exception as e:
            if hasattr(e, 'message'):
                print('Import ERROR {}'.format(e.message))
            else:
                print(e)


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
