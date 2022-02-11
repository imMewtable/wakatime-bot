import DbModel
import constant
import asyncio
import auth
import itertools

def most_used_language(stats):
    """
    Returns a user's most used programming language
    """
    langs = {}
    
    for day in stats['data']:
        if day['languages']:
            language = day['languages'][0]['name']

            if language in langs:
                langs[language] += 1
            else:
                langs[language] = 1

    # find the max (not accounting for a tie... yet)
    if langs:
        mostUsedLang = max(langs, key=langs.get)
        return mostUsedLang
    else: 
        return "No data"


async def rank_all_users(self, ctx, r):
    """
    Returns a sorted list of dictionaries that contain
    every authenticated user in the server
    """

    people = []

    userData = await self.authenticator.async_get_all_wakatime_users_json(ctx.guild.id, r)

    # turn list of tuples into my list of dicts
    for user in userData:
        if r == constant.ALL_TIME:
            textTime = user[1]['data']['text']
            rawTime = user[1]['data']['total_seconds']
        else: 
            textTime = user[1]['cummulative_total']['text']
            rawTime = user[1]['cummulative_total']['seconds']
        
        member = ctx.guild.get_member_named(user[0])
    
        userDict = {}
        userDict['name'] = member.display_name
        userDict['seconds'] = rawTime
        userDict['time'] = textTime

        people.append(userDict)
            
    # Sort the list
    people = sorted(people, key=lambda x: x['seconds'], reverse=True)

    return people

def format_leaderboard(people, n, guild_name):
    count = 0
    leaderboard = "**Top {0} of {1}:**".format(n, guild_name)

    for person in itertools.islice(people, n):
        count += 1
        row = "\n**[{0}]** {1} - *{2}*".format(count, person['name'], person['time'])
        leaderboard += row
    
    return leaderboard
            