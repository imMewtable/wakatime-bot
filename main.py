import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import DbModel
from DbModel import WakaData
import auth
import constant
import json
import data_parser


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


        # HANDLES ALL LEADERBOARDS ARGS
        @self.command(name='top')
        async def leaderboard(ctx):
            pass

        @self.command(name='stats')
        async def stats(ctx, arg):
            """
            Prints out the stats of the user that sends the command
            arg[0]: range (week, month, year, alltime)
            arg[1]: username (OPTIONAL)
            """

            # Time range of stats to be printed
            if arg[0] == 'week' or 'weekly':
                range = constant.WEEK
            elif arg[0] == 'month' or 'monthly':
                range = constant.MONTH
            elif arg[0] == 'year' or 'yearly':
                range = constant.YEAR
            elif arg[0] == 'alltime':
                range = constant.ALL_TIME
            else:
                print("{0} is not an acceptable time range".format(arg[0]))
                await ctx.message.reply("Sorry, I dont recognize {0} as a valid time range. Try \"week\", \"month\", \"year\", or \"alltime\"!".format(arg[0]))

            # Which user's stats to be printed
            if arg[1]:
                user = arg[1]
            else:
                user = ctx.author

            stats = self.authenticator.get_wakatime_user_json(user, ctx.guild.id, range)

            # Top language is not included in alltime stats. Different json formats too
            if range == constant.ALL_TIME:
                start = stats['range'] # I STOPPED HEREEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE
                time = stats['data']['text']
                lang = 'None'
            else:
                time = stats['cummulative_total']['text']
                lang = data_parser.most_used_language(stats)

            # Print results
            if time == "0 secs":
                # Should specify the time range? Not sure.
                 await ctx.message.reply("Sorry, you don't have any data logged yet! Spend some time coding and try again.")
            else:
                await ctx.message.reply("Time: {0} \nMost used language: {1}".format(time, lang))

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