import os
import datetime

from dotenv import load_dotenv
from peewee import *
from playhouse.mysql_ext import MySQLDatabase

load_dotenv('secrets.env')
HOST = os.getenv('MYSQL_HOST')
MYSQL_USERNAME = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
DB_NAME = os.getenv('MYSQL_DATABASE_NAME')

db = MySQLDatabase(
    host=HOST,
    user=MYSQL_USERNAME,
    password=MYSQL_PASSWORD,
    database=DB_NAME
)


class BaseModel(Model):
    """A base model that will use our MySQL database."""

    class Meta:
        database = db


def default_time():
    return datetime.time(0, 0, 0)


# Class that describes how Wakabot will act on a per-server basis
class ServerConfig(BaseModel):
    server_id = BigIntegerField(primary_key=True)                                   # Discord's server id
    display_weekly = BooleanField(null=False, default=False)                        # Automatically display user scoreboard weekly
    display_monthly = BooleanField(null=False, default=False)                       # Automatically display user scoreboard monthly
    user_scoreboard_count = IntegerField(null=False, default=5)                     # Max number of users to display on any given scoreboard
    auto_scoreboard_display = TimeField(null=False, default=default_time) # When to display the scoreboard (UTC) (defaults to 00:00:00 UTC or 7PM EST)


# Class that describes a user that wakabot keeps track of
class WakaData(BaseModel):
    discord_username = CharField(null=False, max_length=40) # Discord member's username
    wakatime_username = CharField(null=True, max_length=40) # Wakatime username (not used for anything rn)
    auth_token = CharField(null=True, max_length=100)       # Access token used to access wakatime API as authenticated user
    refresh_token = CharField(null=True, max_length=100)    # Refresh token used to get new access tokens
    server_id = BigIntegerField(null=False)                 # Discord server ID

    class Meta:
        primary_key = CompositeKey('discord_username', 'server_id')


# Self explanatory
def init_tables():
    db.connect()
    db.create_tables([WakaData, ServerConfig])
    db.close()


# Used when the register command is used. Initializes an entry in the db with the discord_user and serverid that
# requested to be initialized.
def initialize_user_data(discord_user, serverid):
    try:
        db.connect()
        code = WakaData.create(discord_username=discord_user, server_id=serverid)
        db.close()
        return code
    except Exception as e:
        print(e)
        db.close()
        return None


# Used when an admin first tries to use !config command.
# Initializes an entry with the server ID with appropriate defaults
def initialize_server_data(server_id):
    try:
        db.connect()
        code = ServerConfig.create(server_id=server_id)
        db.close()
        return code
    except Exception as e:
        print(e)
        db.close()
        return None


def update_server_config(server_id, display_weekly=None, display_monthly=None,
                         user_scoreboard_count=None, auto_display_scoreboard=None):
    """
    Updates the server's config with the information passed in.
    Parameters are optional other than server_id, which is required.

    :param server_id: discord server's unique id
    :param display_weekly: should be None or True/False
    :param display_monthly: should be None or True/False
    :param user_scoreboard_count: should be an integer
    :param auto_display_scoreboard: must be a time - datetime.time(0, 0, 0)
    :return: an int that    describes how many rows in the DB were changed
    """
    try:
        db.connect()
        data = ServerConfig.get(ServerConfig.server_id == server_id)

        if display_weekly is not None:
            data.display_weekly = display_weekly
        if display_monthly is not None:
            data.display_monthly = display_monthly
        if user_scoreboard_count is not None:
            data.user_scoreboard_count = user_scoreboard_count
        if auto_display_scoreboard is not None:
            data.auto_scoreboard_display = auto_display_scoreboard

        code = data.save()
        db.close()
        return code
    except Exception as e:
        print(e)
        db.close()
        return None


# Used when user is authenticated. Updates dicord_username entry where the auth token is null
def update_user_data(discord_user, wakatime_username, auth_token, refresh_token):
    db.connect()

    data = WakaData.get((WakaData.discord_username == discord_user) & (WakaData.auth_token >> None))
    data.wakatime_username = wakatime_username
    data.auth_token = auth_token
    data.refresh_token = refresh_token

    code = data.save()
    db.close()
    return code


# Updates discord username with server ids tokens
def update_user_tokens(discord_username, server_id, new_auth_token, new_refresh_token):
    db.connect()

    data = WakaData.get((WakaData.discord_username == discord_username) & (WakaData.server_id == server_id))
    data.auth_token = new_auth_token
    data.refresh_token = new_refresh_token

    code = data.save()
    db.close()
    return code


# Returns the WakaData object associated with the discord username and server id
def get_discord_user_data(discord_user, serverid):
    try:
        db.connect()

        data = WakaData.select().where((WakaData.discord_username == discord_user) & (WakaData.server_id == serverid))
        user = data[0]

        db.close()
        return user
    except Exception as e:
        print(e)
        db.close()
        return None


# Checks to see if a user has been initialized in the DB but not fully authenticated.
# This probably happens if the user forgot to paste in the auth token from wakatime OR didn't click the link in time
def is_user_initialized_not_authenticated(discord_username, server_id):
    return get_user_access_token(discord_username, server_id) is None


# Checks to see if a user has been fully authenticated (aka, exists in DB with access token
def is_user_authenticated(discord_username, server_id):
    return get_user_access_token(discord_username, server_id) is not None


# Get's the discord user in server ID's access token
def get_user_access_token(discord_user, server_id):
    try:
        db.connect()

        data = WakaData.select().where((WakaData.discord_username == discord_user) & (WakaData.server_id == server_id))
        access_token = data[0].auth_token

        db.close()
        return access_token
    except Exception as e:
        print(e)
        db.close()
        return None


# Gets the discord user in server id's refresh token
def get_user_refresh_token(discord_username, server_id):
    try:
        db.connect()

        data = WakaData.select().where((WakaData.discord_username == discord_username) &
                                       (WakaData.server_id == server_id))
        refresh_token = data[0].refresh_token

        db.close()
        return refresh_token
    except Exception as e:
        print(e)
        db.close()
        return None


# Gets all discord users who are currently authenticated
def get_authenticated_discord_users(server_id):
    try:
        db.connect()
        data = WakaData.select(WakaData.discord_username).where((WakaData.server_id == server_id) &  # ServerID is equal
                                                                (~WakaData.auth_token >> None))  # auth_token is not None
        db.close()
        return data
    except Exception as e:
        print(e)
        db.close()
        return None


def __debug_log_all_data__():
    db.connect()

    rows = WakaData.select()
    for row in rows:
        print("[{}, {}, {}, {}]".format(row.discord_username, row.wakatime_username, row.auth_token, row.server_id))

    db.close()


def get_user_with_no_access_token(discord_username):
    db.connect()
    data = WakaData.select().where((WakaData.discord_username == discord_username) & (WakaData.auth_token >> None)).get()
    db.close()
    return data

#init_tables()
#__debug_log_all_data__()