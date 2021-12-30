import discord
import os
from dotenv import load_dotenv



class WakaBot(discord.Client):
    def __init__(self):
        super().__init__()


    # Overridden method
    # Called when bot successfully logs onto server
    async def on_ready(self):
        print('We have logged in as {0.user}'.format(client))



# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

client = WakaBot()

client.run(API_TOKEN)