import discord
import os
import api
from dotenv import load_dotenv
from discord.ext import commands


class WakaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')

        # Command to register user
        @self.command(name='register')
        async def waka_register(ctx):
            # method call to auth
            await ctx.message.author.send('Test message')
            await ctx.message.reply("I sent you a DM to continue the registration process!")

        # Command to print the top 5 users of all time
        @self.command(name='alltime')
        async def waka_leaderboard_alltime(ctx):
            pass

        # Command to print the top 5 users of the week
        @self.command(name='weekly')
        async def waka_leaderboard_weekly(ctx):
            pass

        # I want two methods for stats: One with no parameter
        # that gives stats for the user who made the command,
        # and one with a parameter which is the user's stats
        # to be printed
        @self.command(name='stats')
        async def waka_stats(ctx):
            pass

    # Overridden method
    # Called when bot successfully logs onto server
    async def on_ready(self):
        print('We have logged in as {0.user}'.format(client))


# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

client = WakaBot()

client.run(API_TOKEN)