import os

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


class WakaData(BaseModel):
    discord_username = CharField(null=False, max_length=40)
    wakatime_username = CharField(null=True, max_length=40)
    auth_token = CharField(null=True, max_length=100)
    refresh_token = CharField(null=True, max_length=100)
    server_id = BigIntegerField(null=False)

    class Meta:
        primary_key = CompositeKey('discord_username', 'server_id')


class AuthenticationState(BaseModel):
    discord_username = CharField(null=False, max_length=40)
    server_id = BigIntegerField(null=False)
    state = CharField(null=False, max_length=50)

    class Meta:
        primary_key = CompositeKey('discord_username', 'server_id')


# Self explanatory
def init_tables():
    db.connect(reuse_if_open=True)
    db.create_tables([WakaData, AuthenticationState])
    db.close()


# Used when the register command is used. Initializes an entry in the db with the discord_user and serverid that
# requested to be initialized.
def initialize_user_data(discord_username, server_id, state):
    try:
        db.connect(reuse_if_open=True)
        code = AuthenticationState.create(discord_username=discord_username, server_id=server_id, state=state)
        db.close()
        return code
    except Exception as e:
        print(e)
        db.close()
        return None


# Updates discord username with server ids tokens
def update_user_tokens(discord_username, server_id, new_auth_token, new_refresh_token):
    db.connect(reuse_if_open=True)

    data = WakaData.get((WakaData.discord_username == discord_username) & (WakaData.server_id == server_id))
    data.auth_token = new_auth_token
    data.refresh_token = new_refresh_token

    code = data.save()
    db.close()
    return code


# Returns the WakaData object associated with the discord username and server id
def get_discord_user_data(discord_user, serverid):
    try:
        db.connect(reuse_if_open=True)

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
        db.connect(reuse_if_open=True)

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
        db.connect(reuse_if_open=True)

        data = WakaData.select().where((WakaData.discord_username == discord_username) &
                                       (WakaData.server_id == server_id))
        refresh_token = data[0].refresh_token

        db.close()
        return refresh_token
    except Exception as e:
        print(e)
        db.close()
        return None


def get_authenticated_discord_users(server_id, as_is=False):
    """
    Gets all the discord users who are currently authenticated under server_id

    :param server_id: The ID of the server
    :param as_is: OPTIONAL parameter. Defines if the user data should be returned as objects or as just strings.
    :return: Either list of string of discord usernames or a list of WakaData objects (depending on as_is)
    """
    try:
        # Get data from database
        db.connect(reuse_if_open=True)
        data = WakaData.select().where((WakaData.server_id == server_id) &  # ServerID is equal
                                       (~WakaData.auth_token >> None))  # auth_token is not None

        db.close()

        # If we dont pass in as_is, return the data as is
        if as_is:
            return data

        # Put results into string list
        result = []
        for user in data:
            result.append(user.discord_username)

        return result
    except Exception as e:
        print(e)
        db.close()
        return None


def __debug_log_all_data__():
    db.connect(reuse_if_open=True)

    rows = WakaData.select()
    for row in rows:
        print("[{}, {}, {}, {}]".format(row.discord_username, row.wakatime_username, row.auth_token, row.server_id))

    db.close()


def get_user_with_no_access_token(discord_username):
    db.connect(reuse_if_open=True)
    data = WakaData.select().where((WakaData.discord_username == discord_username) & (WakaData.auth_token >> None)).get()
    db.close()
    return data


def update_tokens_from_old_refresh_token(old_refresh_token, new_refresh_token, access_token):
    db.connect(reuse_if_open=True)
    query = WakaData.update(refresh_token=new_refresh_token, auth_token=access_token)\
                    .where(WakaData.refresh_token == old_refresh_token)
    code = query.execute()
    #db.close() For some reason this line slows token refreshing by like 31%
    return code

#init_tables()
#__debug_log_all_data__()
