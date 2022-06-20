from datetime import datetime, timedelta

import requests
import urllib3
from django.conf import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


saved_token = ""
saved_token_valid_till = datetime.now()


def set_globals(token, token_valid_till):
    global saved_token
    global saved_token_valid_till
    saved_token = token
    saved_token_valid_till = token_valid_till


def get_token():
    payload = {
        'client_id': settings.ICD_CLIENT_ID,
        'client_secret': settings.ICD_CLIENT_SECRET,
        'scope': settings.ICD_AUTH_SCOPE,
        'grant_type': settings.ICD_AUTH_GRANT_TYPE
    }

    r = requests.post(settings.ICD_AUTH_ENDPOINT, data=payload, verify=False).json()

    token = r['access_token']
    set_globals(token, datetime.now() + timedelta(seconds=r['expires_in']))
    return token


def get_diseases(search_text):
    token = saved_token if saved_token_valid_till > datetime.now() else get_token()
    headers = {
        'Authorization':  'Bearer ' + token,
        'Accept': 'application/json',
        'Accept-Language': settings.ICD_SEARCH_LANGUAGE,
        'API-Version': settings.ICD_SEARCH_VERSION
    }
    payload = {
        'q': search_text.strip() + '%',
    }

    r = requests.post(settings.ICD_SEARCH_ENDPOINT, headers=headers,
                      data=payload, verify=False).json()
    return [{'id': entity['theCode'], 'name': entity['title'], 'reference_url': entity['id']} for entity in r['destinationEntities']]
