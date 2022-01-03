from peewee import *
import datetime

db = SqliteDatabase('users.db')


class BaseModel(Model):
    """A base model that will use our Sqlite database."""

    class Meta:
        database = db
        primary_key = CompositeKey('discord_username', 'server_id')


class WakaData(BaseModel):
    discord_username = TextField(null=False)
    wakatime_username = TextField(null=True)
    auth_token = TextField(null=True)
    server_id = IntegerField(null=False)


# Self explanatory
def init_tables():
    db.create_tables([WakaData])


# Used when the register command is used. Initializes an entry in the db with the discord_user and serverid that
# requested to be initialized.
def initialize_user_data(discord_user, serverid):
    try:
        return WakaData.create(discord_username=discord_user, server_id=serverid)
    except Exception as e:
        print(e)
        return None


# Used when user is authenticated. Updates dicord_username entry where the auth token is null
def update_user_data(discord_user, wakatime_username, token):
    data = WakaData.get((WakaData.discord_username == discord_user) & (WakaData.auth_token >> None))
    data.wakatime_username = wakatime_username
    data.auth_token = token
    return data.save()


# Returns the WakaData object associated with the discord username and server id
def get_discord_user_data(discord_user, serverid):
    try:
        data = WakaData.select().where((WakaData.discord_username == discord_user) & (WakaData.server_id == serverid))
        return data[0]
    except Exception as e:
        print(e)
        return None


# Get's the discord user in server ID's access token
def get_user_token(discord_user, server_id):
    try:
        data = WakaData.select().where((WakaData.discord_username == discord_user) & (WakaData.server_id == server_id))
        return data[0].auth_token
    except Exception as e:
        return None


# Gets all discord users who are currently authenticated
def get_authenticated_discord_users(server_id):
    try:
        data = WakaData.select(WakaData.discord_username).where((WakaData.server_id == server_id) &  # ServerID is equal
                                                               (~WakaData.auth_token >> None))  # auth_token is not None
        return data
    except Exception as e:
        print(e)
        return None


def __debug_log_all_data__():
    rows = WakaData.select()
    for row in rows:
        print("[{}, {}, {}, {}]".format(row.discord_username, row.wakatime_username, row.auth_token, row.server_id))

# init_tables()
# __debug_log_all_data__()

users = get_authenticated_discord_users(892121935658504232)
for user in users:
    print(user.discord_username)