import discord
import os
from dotenv import load_dotenv
from discord.ext import commands



class WakaBot(discord.Client):
    def __init__(self):
        super().__init__()


    # Overridden method
    # Called when bot successfully logs onto server
    async def on_ready(self):
        print('We have logged in as {0.user}'.format(client))


    # Commands
    bot = commands.bot(command_prefix='!')

    # Command to associate a WakaTime username with a Discord account
    @bot.command(name='waka-register')
    async def waka_register(ctx, name):
        pass

    # Command to print the top 5 users of all time
    @bot.command(name='alltime')
    async def waka_leaderboard_alltime(ctx):
        pass

    #Command to print the top 5 users of the week
    @bot.command(name='weekly')
    async def waka_leaderboard_weekly(ctx):
        pass
    
    # I want two methods for stats: One with no parameter
    # that gives stats for the user who made the command,
    # and one with a parameter which is the user's stats
    # to be printed
    @bot.command(name='stats')
    async def waka_stats(ctx):
        pass



# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

client = WakaBot()

client.run(API_TOKEN)