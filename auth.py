import hashlib
import json
import os
import sys

import requests
from rauth import OAuth2Service
from rauth import *
from dotenv import load_dotenv
from urllib.parse import parse_qsl
import DbModel

class Authorizer:
    def __init__(self):
        load_dotenv('secrets.env')
        APP_ID = os.getenv('WAKA_APP_ID')
        APP_SECRET = os.getenv('WAKA_APP_SECRET')

        self.redirect_uri = 'https://wakatime.com/oauth/test'

        self.base_url = 'https://wakatime.com/api/v1/'

        self.service = OAuth2Service(
            client_id=APP_ID,  # from https://wakatime.com/apps
            client_secret=APP_SECRET,  # from https://wakatime.com/apps
            name='wakatime',
            authorize_url='https://wakatime.com/oauth/authorize',
            access_token_url='https://wakatime.com/oauth/token',
            base_url='https://wakatime.com/api/v1/')

    # Private messages user the link for the authorization token
    def get_user_authorization_url(self):
        params = {'scope': 'email,read_stats,read_logged_time',
                  'response_type': 'code',
                  'redirect_uri': self.redirect_uri}

        url = self.service.get_authorize_url(**params)
        return url

    # Turns raw response object into dictionary for easy parsing
    # Need to do this with token response as token response returns both a access token and refresh token
    def __parse_raw_response__(self, response_text):
        # keys and values are separated with & signs
        response_objects = response_text.split('&')
        parsed_response = {}
        for entry in response_objects:
            # split at = to get proper key/value
            kv = entry.split('=')
            parsed_response[kv[0]] = kv[1]

        return parsed_response

    # Turns the first token given by the user into a refresh token and access token
    def get_first_access_token(self, initial_token):
        headers = {'Accept': 'application/x-www-form-urlencoded'}
        data = {'code': initial_token,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri}
        return self.__parse_raw_response__(self.service.get_raw_access_token(headers=headers, data=data).text)

    # Refreshes a user's database tokens by making call to wakatime token API and updating DB
    def refresh_tokens(self, discord_username, server_id, old_refresh_token):
        headers = {'Accept': 'application/x-www-form-urlencoded'}
        data = {'grant_type' : 'refresh_token',
                'refresh_token': old_refresh_token}
        response = self.__parse_raw_response__(self.service.get_raw_access_token(headers=headers, data=data).text)
        new_refresh_token = response['refresh_token']
        new_access_token = response['access_token']
        DbModel.update_user_tokens(discord_username, server_id, new_access_token, new_refresh_token)

    # Attempts to verify authorization token passed into function from discord_username
    def authorize_token(self, initial_token, discord_username, server_id):
        # Gets token response as dict
        # token_response['access_token'] gets access token
        # token_response['refresh_token'] gets refresh token
        token_response = self.get_first_access_token(initial_token)

        # Use authorization header
        headers = {'Accept': 'application/x-www-form-urlencoded',
                   'Authorization': 'Bearer {}'.format(token_response['access_token'])}

        response = requests.get(self.base_url + 'users/current', headers=headers)
        # Means the token given was valid
        if response.status_code == 200:
            user_data = response.json()['data']
            username = user_data['username']

            # Make sure table data gets updated
            if DbModel.update_user_data(discord_username, username, token_response['access_token'], token_response['refresh_token']) == 1:
                return True

        return False

    # Authenticates and gets the discord users in server id's data.
    # Returns as json if found, returns None if not found or authentication failed
    # Time range is optional and must either be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
    def get_wakatime_user_json(self, discord_username, server_id, time_range=None):
        old_refresh_token = DbModel.get_user_refresh_token(discord_username, server_id)

        # Refresh token prior to accessing API so its always up to date
        self.refresh_tokens(discord_username, server_id, old_refresh_token)
        access_token = DbModel.get_user_access_token(discord_username, server_id)

        # Use authorization header
        headers = {'Accept': 'application/x-www-form-urlencoded',
                   'Authorization': 'Bearer {}'.format(access_token)}

        # Optional time range argument.
        url_args = 'users/current/stats/'
        if time_range is not None:
            url_args + time_range

        # Use get request using authorization header
        response = requests.get(self.base_url + url_args, headers=headers)
        if response.status_code == 200:
            return response.json()['data']

        return None
