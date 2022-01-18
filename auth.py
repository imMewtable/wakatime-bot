import asyncio
import hashlib
import json
import os
import sys
import time

import aiohttp
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
        data = {'grant_type': 'refresh_token',
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
            if DbModel.update_user_data(discord_username, username, token_response['access_token'],
                                        token_response['refresh_token']) == 1:
                return True

        return False

    # Authenticates and gets the discord users in server id's data.
    # Returns as json if found, returns None if not found or authentication failed
    # Time range is REQUIRED and must either be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
    def get_wakatime_user_json(self, discord_username, server_id, time_range):
        ping = time.perf_counter()
        old_refresh_token = DbModel.get_user_refresh_token(discord_username, server_id)

        # Refresh token prior to accessing API so its always up to date
        self.refresh_tokens(discord_username, server_id, old_refresh_token)
        access_token = DbModel.get_user_access_token(discord_username, server_id)

        # Use authorization header
        headers = {'Accept': 'application/x-www-form-urlencoded',
                   'Authorization': 'Bearer {}'.format(access_token)}

        # Need different URL for all-time stats
        if time_range == 'all_time_since_today':
            url_args = 'users/current/all_time_since_today'
        else:
            url_args = 'users/current/summaries?range='
            url_args = url_args + time_range

        # Use get request using authorization header
        response = requests.get(self.base_url + url_args, headers=headers)
        if response.status_code == 200:
            pong = time.perf_counter()
            print(f"Got a response for {discord_username} in {pong - ping:0.4f} seconds")
            return response.json()

        return None

    async def __refresh_all_server_tokens__(self, server_id):
        async with aiohttp.ClientSession() as token_session:
            tasks = []
            headers = {'Accept': 'application/x-www-form-urlencoded'}

            users = DbModel.get_authenticated_discord_users(server_id, as_is=True)
            load_dotenv('secrets.env')
            app_id = os.getenv('WAKA_APP_ID')
            app_secret = os.getenv('WAKA_APP_SECRET')

            for user in users:
                data = {'client_id': app_id,
                        'client_secret': app_secret,
                        'redirect_uri': self.redirect_uri,
                        'grant_type': 'refresh_token',
                        'refresh_token': user.refresh_token}
                tasks.append(asyncio.ensure_future(self.__refresh_single_token__(headers, data,
                                                                                 user.refresh_token, token_session)))

            token_responses = await asyncio.gather(*tasks)
            for response in token_responses:
                http_response = response[0]  # Actual token response
                old_refresh_token = response[1]  # Old refresh token

                DbModel.update_tokens_from_old_refresh_token(old_refresh_token,
                                                             http_response['refresh_token'],
                                                             http_response['access_token'])

    async def __refresh_single_token__(self, header, body, old_refresh_token, session):
        async with session.post(url='https://wakatime.com/oauth/token', data=body, headers=header) as response:
            token_response = self.__parse_raw_response__(await response.text())
            return token_response, old_refresh_token

    async def async_get_wakatime_users_json(self, server_id, time_range):
        asyncio.run(self.__refresh_all_server_tokens__(server_id))
        return asyncio.run(self.__async_get_wakatime_users_json__(server_id, time_range))

    async def __async_get_wakatime_users_json__(self, server_id, time_range):
        async with aiohttp.ClientSession() as session:
            pass


auth = Authorizer()
asyncio.run(auth.__refresh_all_server_tokens__(892121935658504232))