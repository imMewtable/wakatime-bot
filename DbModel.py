from peewee import *
import datetime


db = SqliteDatabase('users.db')

class BaseModel(Model):
    """A base model that will use our Sqlite database."""
    class Meta:
        database = db

class WakaData(BaseModel):
    discord_username = TextField(primary_key=True)
    wakatime_username = TextField()
    auth_token = TextField()


def init_tables():
    db.create_tables([WakaData])


def add_user_data(discord_user, waka_user, token):
    data = WakaData.create(discord_username=discord_user, wakatime_username=waka_user, auth_token=token)
    return data.save()


def get_discord_user_data(discord_user):
    try:
        data = WakaData.get(WakaData.discord_username == discord_user)
        return data
    except Exception as e:
        return None


#init_tables()
#print(get_discord_user_data('jkc_boi#4751'))