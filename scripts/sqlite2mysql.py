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


class MySQLBaseModel(Model):
    """A base model that will use our Sqlite database."""

    class Meta:
        database = mysql_db
        primary_key = CompositeKey('discord_username', 'server_id')


class WakaData(MySQLBaseModel):
    discord_username = UUIDField(null=False)
    wakatime_username = TextField(null=True)
    auth_token = TextField(null=True)
    refresh_token = TextField(null=True)
    server_id = IntegerField(null=False)


mysql_db.connect()

conn = sqlite3.connect('users.db')
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