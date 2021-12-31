import requests
import datetime

#URL = r'https://wakatime.com/api/v1/users/{0}/stats/'

#r = requests.get(URL.format('jkcarney'))
#code = r.status_code
#print(code)
#print(r.json()['data']['human_readable_total'])


def does_wakatime_user_exist(user):
    user_url = URL.format(user)
    r = requests.get(user_url)
    code = r.status_code

    if code == 200:
        return True
    else:
        return False


def is_wakatime_user_codetime_public(user):
    user_url = URL.format(user)
    r = requests.get(user_url)
    code = r.status_code
    response = r.json()['data']

    if code == 200:
        return response['is_coding_activity_visible']

    return None


def get_wakatime_user_total_seconds(user):
    user_url = URL.format(user)
    r = requests.get(user_url)
    code = r.status_code

    if code == 200:
        return r.json()['data']['total_seconds']

    return -1.0
