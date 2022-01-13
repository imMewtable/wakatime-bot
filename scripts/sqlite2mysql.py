import os
import sqlite3

from dotenv import load_dotenv
from peewee import *
from playhouse.mysql_ext import MySQLDatabase

load_dotenv('../secrets.env')
HOST = os.getenv('MYSQL_HOST')
MYSQL_USERNAME = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
DB_NAME = os.getenv('MYSQL_DATABASE_NAME')

mysql_db = MySQLDatabase(
    host=HOST,
    user=MYSQL_USERNAME,
    password=MYSQL_PASSWORD,
    database=DB_NAME
)


class BaseModel(Model):
    """A base model that will use our Sqlite database."""

    class Meta:
        database = mysql_db
        primary_key = CompositeKey('discord_username', 'server_id')


class WakaData(BaseModel):
    discord_username = CharField(null=False, max_length=40)
    wakatime_username = CharField(null=True, max_length=40)
    auth_token = CharField(null=True, max_length=100)
    refresh_token = CharField(null=True, max_length=100)
    server_id = BigIntegerField(null=False)


mysql_db.connect()

conn = sqlite3.connect('../users.db')
c = conn.cursor()

c.execute("SELECT * FROM wakadata")
data = c.fetchall()

for row in data:
    WakaData.create(discord_username=row[0],
                    wakatime_username=row[1],
                    auth_token=row[2],
                    refresh_token=row[3],
                    server_id=row[4])

mysql_db.close()
conn.close()