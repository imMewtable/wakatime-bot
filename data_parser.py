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
