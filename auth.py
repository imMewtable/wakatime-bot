import asyncio
import os
import aiohttp
import requests
import time
import hashlib

from rauth import OAuth2Service
from rauth import *
from dotenv import load_dotenv
import DbModel


class Authorizer:
    def __init__(self):
        load_dotenv('secrets.env')
        self.APP_ID = os.getenv('WAKA_APP_ID')
        self.APP_SECRET = os.getenv('WAKA_APP_SECRET')

        self.redirect_uri = 'https://immewtable.com/authenticate'

        self.base_url = 'https://wakatime.com/api/v1/'

        self.service = OAuth2Service(
            client_id=self.APP_ID,  # from https://wakatime.com/apps
            client_secret=self.APP_SECRET,  # from https://wakatime.com/apps
            name='wakatime',
            authorize_url='https://wakatime.com/oauth/authorize',
            access_token_url='https://wakatime.com/oauth/token',
            base_url='https://wakatime.com/api/v1/')

    def get_user_authorization_url(self, discord_username, server_id):
        """
        Generates an authorization URL for the user to begin the authentication process.
        Also calls the initialization function for the user using the state generated for
        the url.
        :param discord_username: The user's discord username who will receive the URL
        :param server_id: The server id that the user started to register with
        :return: the URL as a string that the user will use to register with wakabot
        """
        state = hashlib.sha1(os.urandom(40)).hexdigest()
        params = {'scope': 'email,read_stats,read_logged_time',
                  'response_type': 'code',
                  'redirect_uri': self.redirect_uri,
                  'state': state}

        url = self.service.get_authorize_url(**params)

        DbModel.initialize_user_data(discord_username, server_id, state)

        return url

    def __parse_raw_response__(self, response_text):
        """
        Turns raw response object into dictionary for easy parsing
        Need to do this with token response as token response returns both a access token and refresh token
        :param response_text:
        :return: the token response as a dictionary
        """
        # keys and values are separated with & signs
        response_objects = response_text.split('&')
        parsed_response = {}
        for entry in response_objects:
            # split at = to get proper key/value
            kv = entry.split('=')
            parsed_response[kv[0]] = kv[1]

        return parsed_response

    def refresh_tokens(self, discord_username, server_id, old_refresh_token):
        """
        Refreshes a user's access token and refresh tokens
        :param discord_username: The discord username to refresh
        :param server_id: The server id to refresh
        :param old_refresh_token: The old refresh token that will be used to refresh the existing tokens
        :return: nothing
        """
        headers = {'Accept': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'refresh_token',
                'refresh_token': old_refresh_token}
        response = self.__parse_raw_response__(self.service.get_raw_access_token(headers=headers, data=data).text)
        new_refresh_token = response['refresh_token']
        new_access_token = response['access_token']
        DbModel.update_user_tokens(discord_username, server_id, new_access_token, new_refresh_token)

    def get_wakatime_user_json(self, discord_username, server_id, time_range):
        """
        Authenticates and gets the discord users in server id's data.
        Returns as json if found, returns None if not found or authentication failed

        :param discord_username: The discord username as a string whose data to retrieve
        :param server_id: the server id the username is in
        :param time_range: The time range to retrieve. must either be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
        :return: Json response of a user's data if it worked, None if it didnt
        """
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
            return response.json()

        return None

    async def __refresh_all_server_tokens__(self, server_id):
        """
        Executes a refresh of all the tokens under server_id.
        Should be used in conjunction with async scoreboard retrieval

        :param server_id: the id of the server whose tokens to refresh
        :return: Nothing
        """
        async with aiohttp.ClientSession() as token_session:
            tasks = []
            headers = {'Accept': 'application/x-www-form-urlencoded'}

            users = DbModel.get_authenticated_discord_users(server_id, as_is=True)

            for user in users:
                # Generate body data
                data = {'client_id': self.APP_ID,
                        'client_secret': self.APP_SECRET,
                        'redirect_uri': self.redirect_uri,
                        'grant_type': 'refresh_token',
                        'refresh_token': user.refresh_token}

                # Call ensure_future to basically "queue up" all the function calls
                tasks.append(asyncio.ensure_future(self.__refresh_single_token__(headers, data,
                                                                                 user.refresh_token, token_session)))

            # This actually executes all the async tasks
            token_responses = await asyncio.gather(*tasks)
            for response in token_responses:
                http_response = response[0]  # Actual token response
                old_refresh_token = response[1]  # Old refresh token

                # Refresh token data.
                DbModel.update_tokens_from_old_refresh_token(old_refresh_token,
                                                             http_response['refresh_token'],
                                                             http_response['access_token'])

    async def __refresh_single_token__(self, header, body, old_refresh_token, session):
        """
        Subroutine to be used in __refresh_all_server_tokens__ to be called with ensure_future
        Asynchronously retrieves a single refresh token response

        :param header: The header of the HTTP request
        :param body: The body or data of the HTTP request
        :param old_refresh_token: The old refresh token that was used to get a new refresh/access token
        :param session: The aio.http client session
        :return: The token response from the token URL and the old refresh token as a tuple
        """
        async with session.post(url='https://wakatime.com/oauth/token', data=body, headers=header) as response:
            token_response = self.__parse_raw_response__(await response.text())
            return token_response, old_refresh_token

    async def async_get_all_wakatime_users_json(self, server_id, time_range):
        """
        Asynchronously retrieves all of the registered users wakatime data.
        Also refreshes all the tokens of the users in server_id
        Should be used with scoreboards in order to speed up response time tremendously.

        :param server_id: The id of the server whos data is to be retrieved
        :param time_range: The time range to retrieve. Must be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
        :return: the json data of each wakatime user under the server_id
        """
        await self.__refresh_all_server_tokens__(server_id)
        return await self.__async_get_wakatime_users_json__(server_id, time_range)

    async def __async_get_wakatime_users_json__(self, server_id, time_range):
        """
        Asynchronously retrieves all of the registered users wakatime data

        :param server_id: The server id from which to retrieve the data
        :param time_range: The time range to retrieve. Must be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
        :return: A list of tuples. 0 index contains the discord username, 1 index contains the json data
        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            users = DbModel.get_authenticated_discord_users(server_id, as_is=True)
            for user in users:
                # Generate authentication header
                header = {'Accept': 'application/x-www-form-urlencoded',
                          'Authorization': 'Bearer {}'.format(user.auth_token)}
                # Call ensure_future to basically "queue up" all the function calls
                tasks.append(asyncio.ensure_future(self.__retrieve_single_wakatime_user_json__(header,
                                                                                               session,
                                                                                               time_range,
                                                                                               user.discord_username)))
            # Execute all queued up tasks
            data_responses = await asyncio.gather(*tasks)
            return data_responses

    async def __retrieve_single_wakatime_user_json__(self, header, session, time_range, discord_username):
        """
        Subroutine that retrieves a single user's json data from the wakatime API asynchronously

        :param header: The authorization header required to get the user's data
        :param session: The aio.http client session
        :param time_range: The time range for data retrieval. Must be nothing, 'last_7_days', 'last_30_days', 'last_6_months', or 'last_year'
        :param discord_username: The discord username that the data is associated with
        :return: A tuple of the discord username and that usernames json data from the wakatime API
        """
        if time_range == 'all_time_since_today':
            url_args = 'users/current/all_time_since_today'
        else:
            url_args = 'users/current/summaries?range='
            url_args = url_args + time_range

        async with session.get(url=self.base_url + url_args, headers=header) as response:
            data = await response.json()
            return discord_username, data


#auth = Authorizer()
#all_user_data = asyncio.run(auth.async_get_all_wakatime_users_json(892121935658504232, 'last_7_days'))

#for user_data in all_user_data:
#    print('USERNAME:\n' + user_data[0])
#    print(user_data[1])