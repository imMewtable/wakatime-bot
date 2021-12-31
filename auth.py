import hashlib
import os
import sys
from rauth import OAuth2Service
from dotenv import load_dotenv
import DbModel


# Checks if discord user is already authorized (meaning they already in the db with token)
def is_discord_user_authorized(discord_username, server_id):
    data = DbModel.get_discord_user_data(discord_username, server_id)

    # If theres an entry and the auth_token field is not none, then they're authorized
    if data is not None and data.auth_token is not None:
        return True
    else:
        return False


class Authorizer:
    def __init__(self):
        load_dotenv('secrets.env')
        APP_ID = os.getenv('WAKA_APP_ID')
        APP_SECRET = os.getenv('WAKA_APP_SECRET')

        self.redirect_uri = 'https://wakatime.com/oauth/test'

        self.service = OAuth2Service(
            client_id=APP_ID,  # from https://wakatime.com/apps
            client_secret=APP_SECRET,  # from https://wakatime.com/apps
            name='wakatime',
            authorize_url='https://wakatime.com/oauth/authorize',
            access_token_url='https://wakatime.com/oauth/token',
            base_url='https://wakatime.com/api/v1/')

    # Private messages user the link for the authorization token
    def get_user_authorization_url(self):
        state = hashlib.sha1(os.urandom(40)).hexdigest()
        params = {'scope': 'email,read_stats',
                  'response_type': 'code',
                  'state': state,
                  'redirect_uri': self.redirect_uri}

        url = self.service.get_authorize_url(**params)
        return url

    # Attempts to verify authorization token passed into function from discord_username
    def authorize_token(self, token, discord_username, server_id):
        headers = {'Accept': 'application/x-www-form-urlencoded'}
        session = self.service.get_auth_session(headers=headers,
                                                data={'code': token,
                                                      'grant_type': 'authorization_code',
                                                      'redirect_uri': self.redirect_uri})

        response = session.get('users/current')
        if response.status_code == 200:
            user_data = response.json()['data']
            username = user_data['username']

            if DbModel.update_user_data(discord_username, username, token) == 1:
                return True
            else:
                return False

        else:
            return False