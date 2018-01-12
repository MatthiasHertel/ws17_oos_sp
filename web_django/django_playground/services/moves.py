from django.conf import settings
import requests


class MovesService:
    """Service that offers Access to MOVES Api - https://dev.moves-app.com ."""

    config = settings.MOVES

    def create_auth(self, code, user):
        """Create first access Token using Smartphone code from callback url."""
        access_token_url = '{}/access_token?grant_type=authorization_code&code={}&client_id={}&client_secret={}'.format(self.config['api_auth'], code, self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            user.moves_access_token = response['access_token']
            user.moves_refresh_token = response['refresh_token']
            user.save()
        else:
            raise Exception(response['error'])

    def get_auth_url(self):
        """Generate Auth URL to connect Smartphone App."""
        return '{}/authorize?response_type=code&client_id={}&scope=activity location'.format(self.config['api_auth'], self.config['client_id'])

    def validate_access_token(self, user):
        """Validate the access token."""
        validate_url = '{}/tokeninfo?access_token={}'.format(self.config['api_auth'], user.moves_access_token)
        response = requests.get(validate_url).json()
        return True if 'error' not in response else False

    def refresh_access_token(self, user):
        """Refresh the access token."""
        access_token_url = '{}/access_token?grant_type=refresh_token&refresh_token={}&client_id={}&client_secret={}'.format(self.config['api_auth'], user.moves_refresh_token, self.config['client_id'], self.config['client_secret'])
        response = requests.post(access_token_url).json()
        if 'error' not in response:
            user.moves_access_token = response['access_token']
            user.moves_refresh_token = response['refresh_token']
            user.save()
        else:
            raise Exception(response['error'])

    def authenticate_user(self, user):
        """Check if user has a valid access token and if not refresh it."""
        if not self.validate_access_token(user):
            self.refresh_access_token(user)

    def get_config(self):
        return settings.MOVES
