import json
import os
from datetime import datetime

from flask import Flask, redirect, request, url_for, render_template, jsonify
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import db

from dotenv import load_dotenv
load_dotenv()

from constants import TEAM_COLOR_MAPPING

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)

assert GOOGLE_CLIENT_ID, "Missing Google Client ID"
assert GOOGLE_CLIENT_SECRET, "Missing Google Client Secret"

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
SCOPES = ["openid", "email", "profile", 'https://www.googleapis.com/auth/calendar']

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return db.get_user(user_id)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard/<user_email>")
def dashboard(user_email):
    return render_template("dashboard.html", user_email=user_email)
    
def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=SCOPES,
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
    print("token_response", token_response.json())
    # Save the credentials for the next run
    with open("token.json", "w") as f:
        f.write(json.dumps(token_response.json()))

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    print("userinfo_response", userinfo_response.json())

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        user_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
    
    user = db.User(
        id_=unique_id, name=users_name, email=user_email, profile_pic=picture
    )

    # Begin user session by logging the user in
    login_user(user)
    db.insert_user(user)

    # Send user back to homepage
    return redirect(url_for("dashboard", user_email=user.email))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/api/users/<user_email>', methods=['GET'])
def api_get_user(user_email):
    return jsonify(db.get_user_by_email(user_email))

@app.route('/api/events', methods=['GET'])
def api_get_events():
    return jsonify(db.get_events())

@app.route('/api/calendars', methods=['GET'])
def api_get_calendars():
    return jsonify(db.get_calendars())

@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    info = request.get_json()
    return jsonify(db.subscribe(info["user_email"], info["calendar_id"]))

@app.route('/api/unsubscribe', methods=['POST'])
def api_unsubscribe():
    info = request.get_json()
    print("info", info)
    return jsonify(db.unsubscribe(info["user_email"], info["calendar_id"]))

@app.route('/google/sync', methods=['POST'])
def google_sync():
    data = request.get_json()

    with open('token.json', 'r') as f:
        token_data = json.load(f)
    
    # Create credentials from the token data
    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )

    service = build("calendar", "v3", credentials=creds)

    page_token, user_email = None, None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for i, calendar_list_entry in enumerate(calendar_list['items']):
            if i == 0:
                user_email = calendar_list_entry['summary']
            elif "thefuncalendar" in calendar_list_entry['summary']:
                # delete existing thefuncalendar
                calendar_id = calendar_list_entry['id']
                service.calendars().delete(calendarId=f"{calendar_id}").execute()
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

    def callback(request_id, response, exception):
        if exception:
            print(f"Error creating event {request_id}: {exception}")
        else:
            print(f"Event created: {response.get('htmlLink')}")

    for calendar in data.keys():
        print("calendar:", calendar)
        # create thefuncalendar with currently selected events
        colorId = None
        try:
            colorId = TEAM_COLOR_MAPPING[calendar.split(" - ")[0].strip()]
        except KeyError:
            print(f"Unknown team color for calendar: {calendar}")
            colorId = 8 # graphite
            
        calendar_info = {
            'summary': calendar + ' via thefuncalendar',
            'timeZone': 'America/Los_Angeles',
            'colorId': colorId,
        }

        created_calendar = service.calendars().insert(body=calendar_info).execute()

        print("created calendar id:", created_calendar['id'])

        # Use batch to insert events
        batch = service.new_batch_http_request()

        print("num events:", len(data[calendar]))
        for raw_event in data[calendar]:
            date = raw_event['date']
            time = raw_event['time']
            start_time, end_time = time.split('-')
            start_date_obj = datetime.strptime(f"{date} {start_time}", "%m/%d/%Y %H:%M")
            formatted_start_time = start_date_obj.strftime("%Y-%m-%dT%H:%M:%S")

            end_date_obj = datetime.strptime(f"{date} {end_time}", "%m/%d/%Y %H:%M")
            formatted_end_time = end_date_obj.strftime("%Y-%m-%dT%H:%M:%S")

            google_event = {
                'summary': raw_event['title'],
                'location': raw_event['location'],
                'start': {
                    'dateTime': formatted_start_time,
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': formatted_end_time,
                    'timeZone': 'America/Los_Angeles',
                },
                'colorId': colorId,
            }

            batch.add(
                service.events().insert(calendarId=created_calendar['id'], body=google_event),
                callback=callback
            )

        try:
            batch.execute()
        except SystemExit as e:
            print(f"THROTTLING ERROR")
            print("TODO: handle throttling with exponential backoff")
            print("FOR NOW: wait and retry in about 1 minute")

    return redirect(f"/dashboard/{user_email}")

if __name__ == "__main__":
    app.run(ssl_context="adhoc")