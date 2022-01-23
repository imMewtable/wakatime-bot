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
            if not DbModel.is_user_authenticated(str(cmd_author), server_id):
                # Get authorization url initializes the user's information in the auth state DB
                url = self.authenticator.get_user_authorization_url(str(cmd_author), server_id)
                await cmd_author.send("Please visit {0} in your browser and allow Wakabot to access your Wakatime "
                                      "data. Once you've done that, you are ready to use Wakabot commands in the "
                                      "server you are registered in!".format(url));
                await ctx.message.reply("I sent you a DM to continue the registration process!")
            else:
                await cmd_author.send('You either already requested to be initialized or you are already authenticated')

        # HANDLES ALL LEADERBOARDS ARGS
        @self.command(name='top')
        async def leaderboard(ctx, *args):
            """
            Prints a leaderboard for server stats 
            args[0]: range (week, month, alltime)
            args[1]: amount of people to print? 
            """
            # Validate args
            if len(args) == 1:
                n = 5
            else:
                n = args[1]

            r = args[0]
          
            if r == 'week' or r =='weekly':
                range = constant.WEEK        
                r = "week"                              
            elif r == 'month' or r == 'monthly':
                range = constant.MONTH
                r = "month"
            elif r == 'alltime':
                range = constant.ALL_TIME
            else:
                print("{0} is not an acceptable time range, command failed.".format(r))
                await ctx.message.reply("Sorry, I dont recognize **{0}** as a valid time range. Try `week`, `month`, or `alltime`!".format(r))
                return

            people = data_parser.rank_all_users(self, ctx, range)

            board = data_parser.format_leaderboard(people, n, ctx.guild.name)
            
            await ctx.message.reply(board)
            
        
        # HANDLES ALL INDIVIDUAL STAT ARGS
        @self.command(name='stats')
        async def stats(ctx, r, user: discord.Member):
            """
            Prints out individual coding stats for a user
            r: range (week, month, alltime)
            user: user whose stats to print
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

            # Check user is registered and in database
            if DbModel.is_user_authenticated(user, ctx.guild.id) is False:
                await ctx.message.reply("Sorry, I can't find {0} in my database. If they have a Wakatime account, they can use the command: `!register` to start that process.".format(user.nick))
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


# Load secrets file and get token
load_dotenv('secrets.env')
API_TOKEN = os.getenv('DISCORD_TOKEN')

DbModel.init_tables()

intents = discord.Intents.default()
intents.members = True

client = WakaBot()
client.run(API_TOKEN)
DbModel.db.close()