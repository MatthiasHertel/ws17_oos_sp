from flask import Flask, request, redirect, url_for

import requests
import os

import config

app = Flask(__name__)

auth = None

if config.access_token:
    auth = dict(access_token=config.access_token)

@app.route("/")
def hello():
    return "Hello World!"


@app.route("/lastweek")
def lastweek():
    global auth
    if auth:
        url = '{}/user/summary/daily/{}'.format(config.api, '2018-W01')  # hardcoded test
        r = requests.get(url, headers = {'Authorization':  'Bearer {}'.format(auth['access_token'])})
        return r.text
    else:
        return 'No Auth', 500

@app.route("/register")
def register():
    if 'code' in request.args:
        access_token_url = '{}/oauth/v1/access_token?grant_type=authorization_code&code={}&client_id={}&client_secret={}'.format(config.api_base, request.args.get('code'), config.client_id, config.client_secret)
        r = requests.post(access_token_url)
        json_r = r.json()
        if 'error' not in json_r:
            global auth
            auth = json_r
            return auth['access_token'], 200
        else:
            return json_r['error'], 400
    elif 'error' in request.args:
        return 'Error code {}'.format(request.args.get('error')), 400
    else:
        return 'Unknown Error', 500


app.run(host=os.getenv('IP', 'localhost'),
        port=int(os.getenv('PORT', 5000)))