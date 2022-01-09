import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import DbModel
from DbModel import WakaData
import auth
import constant
import json


class WakaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!')
        self.authenticator = auth.Authorizer()

        # Command to register user
        @self.command(name='register')
        async def waka_register(ctx):
            server_id = ctx.guild.id
            cmd_author = ctx.message.author
            # initialize_user_data returns the record that was successfully created
            # If it didn't work, it returns None. So if it's not None, it worked.
            if DbModel.initialize_user_data(str(cmd_author), server_id):
                url = self.authenticator.get_user_authorization_url()
                await cmd_author.send("Please visit {} and authorize Wakabot to use your API data.\n\nOnce you've "
                                      "done that, the wakatime website should give you a token.\n\nCopy that token, "
                                      "come back here, paste it into the chat and private message me the token in "
                                      "order to finish the authentication process.".format(url)) 
                await ctx.message.reply("I sent you a DM to continue the registration process!")
            else:
                await cmd_author.send('You either already requested to be initialized or you are already authenticated')

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
        # to be printed. no clue how to differentiate...

        # second arg (assuming usernam was put 1st) can be the range
        # ill have to make if statement for that to check if the first arg is only range
        @self.command(name='stats')
        async def waka_stats(ctx, arg):
            # check if args or not. No args = use message author
            # ASSUMING ARG LIST CAN BE EMPTY LMAO
            if arg:
                f = open(auth.get_wakatime_user_json(self, arg[0], ctx.guild, constant.WEEK))
                data = json.load(f)
            else:
                f = open (auth.get_wakatime_user_json(self, ctx.author, ctx.guild, constant.WEEK))
                data = json.load(f)


    # Overridden method
    # Called when bot successfully logs onto server
    async def on_ready(self):
        print('We have logged in as {0.user}'.format(client))

    # On message for DMs
    async def on_message(self, message):
        if message.author == client.user:
            return

        # on_message event fires for guild messages and DMs. So if we get an on_message we still need to process it
        # as a potential command (aka, inherited process_commands function)
        await client.process_commands(message)

        # Basically checking if its a DM by seeing if the message has a guild
        if not message.guild:
            msg_author = str(message.author)
            token = str(message.content)
            data = WakaData.select().where((WakaData.discord_username == msg_author) & (WakaData.auth_token >> None)).get()
            # If the user is in the DB and the auth token hasn't been initialized
            if data:
                server = data.server_id
                # Authenticates token
                if self.authenticator.authorize_token(token, msg_author, server):
                    await message.reply('Successfully authenticated! Have a good day :)')
                else:
                    await message.reply('Failed to authenticate token. Was there a typo in the token?')
            else:
                await message.reply('Your information was not found in the database. Please use !register first to '
                                    'initiate the authentication.')


# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

DbModel.init_tables()

client = WakaBot()
client.run(API_TOKEN)