import DbModel
import constant

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


def rank_all_users(self, guild_ID, r):
    """
    Returns a sorted list of dictionaries that contain
    every authenticated user in the server
    """

    people = []

    authUsers = DbModel.get_authenticated_discord_users(guild_ID)

    # Collect data from json into my list of dicts
    for username in authUsers:
        stats = self.authenticator.get_wakatime_user_json(username, guild_ID, r)

        if r == constant.ALL_TIME:
            textTime = stats['data']['text']
            rawTime = stats['data']['total_seconds']
        else: 
            textTime = stats['cummulative_total']['text']
            rawTime = stats['cummulative_total']['seconds']
                
        userDict = {}
        userDict['name'] = username.display_name
        userDict['seconds'] = rawTime
        userDict['time'] = textTime

        people.append(userDict)
            
    # Sort the list
    people = sorted(people, key=lambda x: x['seconds'])

    return people

def format_leaderboard(people, n, guild_name):
    count = 0
    leaderboard = "**Top {0} of {1}:**".format(n, guild_name)

    for person in people:
        count += 1
        temp = "\n**[{0}]** {1} - *{2}*".format(count, person['name'], person['time'])
        leaderboard += temp
        if count == n:
            break
    
    return leaderboard
            