import os

from dotenv import load_dotenv
from peewee import *
from playhouse.mysql_ext import MySQLDatabase

load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

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
    """A base model that will use our Sqlite database."""

    class Meta:
        database = db
        primary_key = CompositeKey('discord_username', 'server_id')


class WakaData(BaseModel):
    discord_username = UUIDField(null=False)
    wakatime_username = TextField(null=True)
    auth_token = TextField(null=True)
    refresh_token = TextField(null=True)
    server_id = IntegerField(null=False)


# Self explanatory
def init_tables():
    db.connect()
    db.create_tables([WakaData])
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
        return None


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
        return None


def __debug_log_all_data__():
    db.connect()

    rows = WakaData.select()
    for row in rows:
        print("[{}, {}, {}, {}]".format(row.discord_username, row.wakatime_username, row.auth_token, row.server_id))

    db.close()

#init_tables()
# __debug_log_all_data__()

print('Attempting to connect to MySQL database...')
did_connect = db.connect()
print(str(did_connect) + ' - If this is TRUE, then the connection succeeded.')
print('Closing DB connection')
db.close()
