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
        super().__init__(command_prefix='!', intents=intents)
        self.authenticator = auth.Authorizer()

        # Command to register user
        @self.command(name='register')
        async def waka_register(ctx):
            server_id = ctx.guild.id
            cmd_author = ctx.message.author
            # initialize_user_data returns the record that was successfully created
            # If it didn't work, it returns None. So if it's not None, it worked.
            # OR, we check if the user is initialized in the database but NOT authenticated (meaning auth_token is None)
            if DbModel.initialize_user_data(str(cmd_author), server_id) or DbModel.is_user_initialized_not_authenticated(str(cmd_author), server_id):
                url = self.authenticator.get_user_authorization_url()
                await cmd_author.send("HERE ARE THE STEPS TO AUTHORIZE YOURSELF WITH THE WAKABOT:\n\n1). Visit the "
                                      "URL at the bottom of this message.\n\n2). Allow Wakabot to be able to read "
                                      "your user data\n\n**3.) Once you have authorized, Wakatime should give you an "
                                      "initial access token (It will look like sec_###...). Copy that token as is, "
                                      "paste it into THIS private "
                                      "message, and send it to me.**\n\n4.) Once that is done, I should inform you "
                                      "that you have successfully authenticated. You are ready to use Wakabot "
                                      "commands on the server you have registered in.\n\n||{}||".format(url))
                await ctx.message.reply("I sent you a DM to continue the registration process!")
            else:
                await cmd_author.send('You either already requested to be initialized or you are already authenticated')

        # HANDLES ALL LEADERBOARDS ARGS
        @self.command(name='top')
        async def leaderboard(ctx):
            pass
        
        # HANDLES ALL INDIVIDUAL STAT ARGS
        @self.command(name='stats')
        async def stats(ctx, r, user: discord.Member):
            """
            Prints out the stats of the user that sends the command
            args[0]: range (week, month, year, alltime)
            args[1]: username (OPTIONAL)
            """
            # Time range of stats to be printed
            if r == 'week' or r =='weekly': # there is no keyword to get the actual current week
                range = constant.WEEK                   # i will have to make a method in future to calc the most recent
                r = "week"                              # sunday and then i will put a custome range here. last 7 from today
                                                        # is stinky and no good 
            elif r == 'month' or r == 'monthly':
                range = constant.MONTH
                r = "month"
            elif r == 'alltime':
                range = constant.ALL_TIME
            else:
                print("{0} is not an acceptable time range, command failed.".format(r))
                await ctx.message.reply("Sorry, I dont recognize **{0}** as a valid time range. Try `week`, `month`, or `alltime`!".format(r))
                return


            stats = self.authenticator.get_wakatime_user_json(user, ctx.guild.id, range)
            
            # Top language is not included in alltime stats. Different json formats too
            if range == constant.ALL_TIME:
                start = stats['data']['range']['start_text']
                start = start[4:] # Cut off the weekday, I dont like it there
                time = stats['data']['text']
                lang = 'None'
            else:
                time = stats['cummulative_total']['text']
                lang = data_parser.most_used_language(stats)

            # Print results
            if time == "0 secs":
                # Should specify the time range? Not sure.
                 await ctx.message.reply("Sorry, you don't have any data logged yet! Spend some time coding and try again.")
            elif lang == "None":
                await ctx.message.reply("**{0}** has coded for **{1}** since **{2}**".format(user.nick, time, start))
            else:
                await ctx.message.reply("**{0}** has coded for **{1}** this {2} \nMost used language: {3}".format(user.nick, time, r, lang))

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
            await message.reply('I have received your token. Please give me a moment while I authenticate you...')
            msg_author = str(message.author)
            token = str(message.content)
            data = DbModel.get_user_with_no_access_token(msg_author)
            # If the user is in the DB and the auth token hasn't been initialized
            if data:
                server = data.server_id
                # Authenticates token
                if self.authenticator.authorize_token(token, msg_author, server):
                    await message.reply('Successfully authenticated! You are now ready to use Wakabot commands on the '
                                        'server you registered in. Have a good day :)')
                else:
                    await message.reply('Failed to authenticate token. Was there a typo in the token?')
            else:
                await message.reply('Your information was not found in the database. Please use !register first to '
                                    'initiate the authentication. Or you were already authenticated ;)')


# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

DbModel.init_tables()

intents = discord.Intents.default()
intents.members = True

client = WakaBot()
client.run(API_TOKEN)
DbModel.db.close()