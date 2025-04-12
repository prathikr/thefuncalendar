#!/usr/bin/python
import sqlite3
import requests
import datetime
from dateutil import parser
import pytz
import os
from dotenv import load_dotenv
load_dotenv()

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id_=-1, name="", email="", profile_pic=""):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

def connect_to_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row # allows us to access columns by name
    return conn

def create_db_table():
    try:
        conn = connect_to_db()
        conn.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY NOT NULL,
                email TEXT NOT NULL,
                calendars TEXT
            );
            
        ''')
        conn.commit()
        conn.execute('''
            CREATE TABLE calendars (
                calendar_id INTEGER PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                events TEXT,
                organization TEXT NOT NULL,
                season TEXT NOT NULL
            );
            
        ''')
        conn.commit()
        conn.execute('''
            CREATE TABLE events (
                event_id INTEGER PRIMARY KEY NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                calendar_id INTEGER NOT NULL,
                description TEXT
            );
            
        ''')
        conn.commit()
        print("User table created successfully")
    except Exception as e:
        print("User table creation failed")
        print(e)
    finally:
        conn.close()

def insert_user(user):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email) VALUES (?)", (user.email,))
    conn.commit()
    user_id = cur.lastrowid

    return user_id

def get_user(user_id):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    user = cur.fetchone()

    return user

def get_user_by_email(user_email):
    user = {}
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (user_email,))
    row = cur.fetchone()

    if not row:
        print("***NEW USER DETECTED***")
        print(f"Creating new account for {user_email}")
        insert_user(User(email=user_email))
        return user

    # convert row object to dictionary
    user["user_id"] = row["user_id"]
    user["email"] = row["email"]
    user["calendars"] = []

    calendars = row["calendars"].split() if row["calendars"] else []
    
    for calendar_id in calendars:
        cur.execute("SELECT * FROM calendars WHERE calendar_id = ?", (calendar_id,))
        conn.commit()
        rows = cur.fetchall()
        for i in rows:
            user["calendars"].append(i["calendar_id"])

    return user

def subscribe(user_email, calendar_id):
    # Clean the email parameter
    if '#' in user_email:
        user_email = user_email.split('#')[0]
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (user_email,))
        row = cur.fetchone()

        calendars = row["calendars"].split() if row["calendars"] else []
        if not (str(calendar_id) in calendars):
            calendars.append(str(calendar_id))
            cur.execute("UPDATE users SET calendars = ? WHERE email = ?",  
                        (" ".join(calendars), user_email,))
            conn.commit()
    except Exception as e:
        print("Error subscribing to calendar")
        print(e)
    finally:
        conn.close()

def unsubscribe(user_email, calendar_id):
    # Clean the email parameter
    if '#' in user_email:
        user_email = user_email.split('#')[0]
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (user_email,))
        row = cur.fetchone()

        calendars = row["calendars"].split() if row["calendars"] else []
        if str(calendar_id) in calendars:
            calendars.remove(str(calendar_id))
            cur.execute("UPDATE users SET calendars = ? WHERE email = ?",  
                        (" ".join(calendars), user_email,))
            conn.commit()
    except Exception as e:
        print("Error unsubscribing from calendar")
        print(e)
    finally:
        conn.close()

def insert_calendar(calendar, check_duplicates=False):
    calendar_id = None
    try:
        conn = connect_to_db()
        cur = conn.cursor()

        # Insert new calendar
        cur.execute("INSERT INTO calendars (name, organization, season) VALUES (?, ?, ?)", (calendar['name'], calendar['organization'], calendar['season'],))
        conn.commit()
        calendar_id = cur.lastrowid

        event_ids = []
        for event in calendar['events']:
            cur.execute("INSERT INTO events (title, location, date, time, calendar_id, description) VALUES (?, ?, ?, ?, ?, ?)", 
                        (event['title'], event['location'], event['date'], event['time'], calendar_id, event.get("description", ""),))
            conn.commit()
            event_ids.append(str(cur.lastrowid))

            cur.execute("UPDATE calendars SET events = ? WHERE calendar_id = ?",  
                    (" ".join(event_ids), calendar_id,))
            conn.commit()
    except:
        conn().rollback()

    finally:
        conn.close()

    return calendar_id

def get_calendars():
    calendars = []
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM calendars")
    rows = cur.fetchall()

    # convert row objects to dictionary
    for i in rows:
        calendar = {}
        calendar["calendar_id"] = i["calendar_id"]
        calendar["name"] = i["name"]
        calendar["events"] = []
        calendar["organization"] = i["organization"]
        calendar["season"] = i["season"]

        event_ids = i["events"].split()
        for event_id in event_ids:
            cur.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            rows = cur.fetchall()
            for i in rows:
                event = {}
                event["event_id"] = i["event_id"]
                event["title"] = i["title"]
                event["location"] = i["location"]
                event["date"] = i["date"]
                event["time"] = i["time"]
                event["calendar_id"] = i["calendar_id"]
                event["description"] = i["description"]
                calendar["events"].append(event)
        calendars.append(calendar)

    return calendars

def get_events():
    events = []
    try:
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM events")
        rows = cur.fetchall()

        for i in rows:
            event = {}
            event["event_id"] = i["event_id"]
            event["title"] = i["title"]
            event["location"] = i["location"]
            event["date"] = i["date"]
            event["time"] = i["time"]
            event["calendar_id"] = i["calendar_id"]
            events.append(event)
    except Exception as e:
        print("Error getting events")
        print(e)
        events = []

    return events

def UTC_to_PST(utc_datetime):
    utc_datetime = parser.parse(utc_datetime)
            
    # Make sure it's treated as UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=pytz.UTC)
    
    # Convert to PST
    pst_timezone = pytz.timezone('America/Los_Angeles')
    pst_datetime = utc_datetime.astimezone(pst_timezone)
    
    # Format date as "MM/DD/YYYY"
    date_formatted = pst_datetime.strftime("%m/%d/%Y")
    
    # Get start time in PST
    start_time = pst_datetime.strftime("%H:%M")
    
    # For end time, let's assume games last 2.5 hours
    end_datetime = pst_datetime + datetime.timedelta(hours=2.5)
    end_time = end_datetime.strftime("%H:%M")
    
    # Format time as "HH:MMPST-HH:MMPST"
    time_formatted = f"{start_time}-{end_time}"

    return date_formatted, time_formatted

def IST_to_PST(match_date, match_time):
    # Parse match date (format: "10-Apr")
    date_parts = match_date.split('-')
    day = int(date_parts[0])
    month_abbr = date_parts[1]
    
    # Get current year (since it's not provided in the data)
    current_year = datetime.datetime.now().year
    
    # Create full date string
    full_date_str = f"{day} {month_abbr} {current_year}"
    full_date = datetime.datetime.strptime(full_date_str, "%d %b %Y")
    
    # Format date as MM/DD/YYYY
    date_formatted = full_date.strftime("%m/%d/%Y")
    
    # Parse match time (format: "11:00 AM")
    time_obj = datetime.datetime.strptime(match_time, "%I:%M %p")
    
    # Combine date and time
    ist_datetime = datetime.datetime.combine(full_date.date(), time_obj.time())
    
    # Convert IST to PST (IST is UTC+5:30, PST is UTC-8, so 13.5 hours difference)
    time_diff = 12.5  # hours
    pst_datetime = ist_datetime - datetime.timedelta(hours=time_diff)
    
    # Format start time in PST
    start_time = pst_datetime.strftime("%I:%M")
    
    # End time (assuming 4 hour match)
    end_datetime = pst_datetime + datetime.timedelta(hours=4)
    end_time = end_datetime.strftime("%I:%M")
    
    # Format the time range
    time_formatted = f"{start_time}-{end_time}"
    
    return time_formatted, date_formatted


def UFC_timezone(ufc_datetime):
    ufc_datetime = parser.parse(ufc_datetime)
    
    # Format date as "MM/DD/YYYY"
    date_formatted = ufc_datetime.strftime("%m/%d/%Y")
    
    # Get start time in PST, adding 1 hour
    ufc_datetime = ufc_datetime + datetime.timedelta(hours=1)
    start_time = ufc_datetime.strftime("%H:%M")
    
    # For end time, let's assume games last 2.5 hours
    end_datetime = ufc_datetime + datetime.timedelta(hours=2.5)
    end_time = end_datetime.strftime("%H:%M")
    
    # Format time as "HH:MMPST-HH:MMPST"
    time_formatted = f"{start_time}-{end_time}"

    return date_formatted, time_formatted

def get_schedule(schedule_url, stadiums_url, team_info_url, api_key):
    stadiums_response = requests.get(stadiums_url, params={"key": api_key})
    if stadiums_response.status_code == 200:
        stadiums_data = stadiums_response.json()
        stadiums_map = {stadium["StadiumID"]: stadium["Name"] for stadium in stadiums_data}
    else:
        print(f"Error fetching stadiums: {stadiums_response.status_code}")
        print(stadiums_response.text)
        stadiums_map = {}

    schedule_response = requests.get(schedule_url, params={"key": api_key})
    if schedule_response.status_code == 200:
        data = schedule_response.json()
        print(f"\nTotal games retrieved: {len(data)}")
    else:
        print(f"Error: Received status code {schedule_response.status_code}")
        print(schedule_response.text)
        return {}
    
    team_info_response = requests.get(team_info_url, params={"key": api_key})
    if team_info_response.status_code == 200:
        team_info = team_info_response.json()
        print(f"\nTotal teams retrieved: {len(team_info)}")
    else:
        print(f"Error: Received status code {team_info_response.status_code}")
        print(team_info_response.text)
        return {}
    
    team_info_clean = {}
    for team in team_info:
        team_info_clean[team["Key"]] = team["Name"]

    schedule = {}
    for game in data:
        if game["HomeTeam"] == "BYE" or game["AwayTeam"] == "BYE":
            print(f"Skipping game with BYE teams: {game}")
            continue

        home_team_id = team_info_clean[game["HomeTeam"]]
        away_team_id = team_info_clean[game["AwayTeam"]]

        if home_team_id not in schedule:
            schedule[home_team_id] = []
        if away_team_id not in schedule:
            schedule[away_team_id] = []

        if not game["DateTimeUTC"]:
            print(f"Skipping game with missing time: {game}")
            continue

        date_formatted, time_formatted = UTC_to_PST(game["DateTimeUTC"])

        stadium_name = stadiums_map.get(game["StadiumID"], "TBD")

        event = {
            "title": f"{home_team_id} vs {away_team_id}",
            "location": stadium_name,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[home_team_id].append(event)

        event = {
            "title": f"{away_team_id} @ {home_team_id}",
            "location": stadium_name,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[away_team_id].append(event)

    return schedule

def get_soccer_schedule(schedule_url, venues_url, team_info_url, api_key, league):
    venues_response = requests.get(venues_url, params={"key": api_key})
    if venues_response.status_code == 200:
        venues_data = venues_response.json()
        venues_map = {venue["VenueId"]: venue["Name"] for venue in venues_data}
    else:
        print(f"Error fetching venues: {venues_response.status_code}")
        print(venues_response.text)
        venues_map = {}

    schedule_response = requests.get(schedule_url, params={"key": api_key})
    if schedule_response.status_code == 200:
        data = schedule_response.json()
        print(f"\nTotal games retrieved: {len(data)}")
    else:
        print(f"Error: Received status code {schedule_response.status_code}")
        print(schedule_response.text)
        return {}
    
    team_info_response = requests.get(team_info_url, params={"key": api_key})
    if team_info_response.status_code == 200:
        team_info = team_info_response.json()
        print(f"\nTotal teams retrieved: {len(team_info)}")
    else:
        print(f"Error: Received status code {team_info_response.status_code}")
        print(team_info_response.text)
        return {}
    
    team_info_clean = {}
    for team in team_info:
        team_info_clean[team["TeamId"]] = team["Name"]

    schedule = {}
    for game in data:
        home_team_id = team_info_clean[game["HomeTeamId"]]
        away_team_id = team_info_clean[game["AwayTeamId"]]

        if home_team_id not in schedule:
            schedule[home_team_id] = []
        if away_team_id not in schedule:
            schedule[away_team_id] = []

        if not game["DateTime"]:
            print(f"Skipping game with missing time: {game}")
            continue

        date_formatted, time_formatted = UTC_to_PST(game["DateTime"])

        venue_name = venues_map.get(game["VenueId"], "TBD")

        event = {
            "title": f"{home_team_id} vs {away_team_id}",
            "location": venue_name,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[home_team_id].append(event)

        event = {
            "title": f"{away_team_id} @ {home_team_id}",
            "location": venue_name,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[away_team_id].append(event)

    return schedule

def get_ipl_schedule():
    urls = ["https://cricket-live-line1.p.rapidapi.com/recentMatches", "https://cricket-live-line1.p.rapidapi.com/upcomingMatches"]

    CRICKET_API_KEY = os.environ.get("CRICKET_API_KEY", None)
    assert CRICKET_API_KEY is not None, "Missing cricket API key"
    
    headers = {
        "x-rapidapi-key": CRICKET_API_KEY, 
        "x-rapidapi-host": "cricket-live-line1.p.rapidapi.com"
    }
    
    # Fetch data from both URLs
    raw_schedule = []
    for url in urls:
        response = requests.get(url, headers=headers)
        
        data = response.json()
        raw_schedule.extend(data['data'])
    
    schedule = {}
    
    for match in raw_schedule:
        if match['series'] != "Indian Premier League 2025":
            continue

        home_team = match['team_a']
        away_team = match['team_b']
        
        # Parse date and time
        match_date = match['match_date']
        match_time = match['match_time']
        time_formatted, date_formatted = IST_to_PST(match_date, match_time)
        
        # Get venue
        venue = match['venue']
        
        # Add to schedule
        if home_team not in schedule:
            schedule[home_team] = []
        if away_team not in schedule:
            schedule[away_team] = []
        
        # Home team event
        home_event = {
            "title": f"{home_team} vs {away_team}",
            "location": venue,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[home_team].append(home_event)
        
        # Away team event
        away_event = {
            "title": f"{away_team} @ {home_team}",
            "location": venue,
            "date": date_formatted,
            "time": time_formatted
        }
        schedule[away_team].append(away_event)
    
    return schedule

def get_mlb_schedule():
    schedule_url = f"https://api.sportsdata.io/v3/mlb/scores/json/SchedulesBasic/2025"
    stadiums_url = "https://api.sportsdata.io/v3/mlb/scores/json/Stadiums"
    team_info_url = "https://api.sportsdata.io/v3/mlb/scores/json/AllTeams"

    MLB_API_KEY = os.environ.get("MLB_API_KEY", None)
    assert MLB_API_KEY is not None, "Missing MLB API key"

    return get_schedule(schedule_url, stadiums_url, team_info_url, MLB_API_KEY)

def get_nba_schedule():
    schedule_url = f"https://api.sportsdata.io/v3/nba/scores/json/SchedulesBasic/2025"
    stadiums_url = "https://api.sportsdata.io/v3/nba/scores/json/Stadiums"
    team_info_url = "https://api.sportsdata.io/v3/nba/scores/json/AllTeams"
    
    NBA_API_KEY = os.environ.get("NBA_API_KEY", None)
    assert NBA_API_KEY is not None, "Missing NBA API key"

    return get_schedule(schedule_url, stadiums_url, team_info_url, NBA_API_KEY)

def get_nfl_schedule():
    schedule_url = f"https://api.sportsdata.io/v3/nfl/scores/json/SchedulesBasic/2024REG"
    stadiums_url = "https://api.sportsdata.io/v3/nfl/scores/json/Stadiums"
    team_info_url = "https://api.sportsdata.io/v3/nfl/scores/json/AllTeams"
    
    NFL_API_KEY = os.environ.get("NFL_API_KEY", None)
    assert NFL_API_KEY is not None, "Missing NFL API key"

    return get_schedule(schedule_url, stadiums_url, team_info_url, NFL_API_KEY)

def get_nhl_schedule():
    schedule_url = f"https://api.sportsdata.io/v3/nhl/scores/json/SchedulesBasic/2025"
    stadiums_url = "https://api.sportsdata.io/v3/nhl/scores/json/Stadiums"
    team_info_url = "https://api.sportsdata.io/v3/nhl/scores/json/AllTeams"
    
    NHL_API_KEY = os.environ.get("NHL_API_KEY", None)
    assert NHL_API_KEY is not None, "Missing NHL API key"

    return get_schedule(schedule_url, stadiums_url, team_info_url, NHL_API_KEY)

def get_soccer_league_schedule(league):
    schedule_url = f"https://api.sportsdata.io/v4/soccer/scores/json/SchedulesBasic/{league}/2025"
    venues_url = "https://api.sportsdata.io/v4/soccer/scores/json/Venues"
    team_info_url = f"https://api.sportsdata.io/v4/soccer/scores/json/Teams/{league}"
    
    SOCCER_API_KEY = os.environ.get("SOCCER_API_KEY", None)
    assert SOCCER_API_KEY is not None, "Missing Soccer API key"

    return get_soccer_schedule(schedule_url, venues_url, team_info_url, SOCCER_API_KEY, league)

def add_schedule_to_db(schedule, organization, season, check_duplicates=False):
    for team, events in schedule.items():
        calendar = {
            "name": team,
            "events": events,
            "organization": organization,
            "season": season
        }
        print(f"Creating calendar for {team}")
        try:
            # Check if the team name exists in teams.txt
            with open("teams.txt", "a+") as f:
                f.seek(0)  # Go to beginning of file to read
                existing_teams = f.read().splitlines()
                
                # If team is not in the file, add it (only for soccer teams)
                if team not in existing_teams:
                    f.write(f"{team}\n")
        except Exception as e:
            print(f"Error writing to soccer_teams.txt: {e}")
        _ = insert_calendar(calendar, check_duplicates)

def get_ufc_schedule():
    schedule_url = "https://api.sportsdata.io/v3/mma/scores/json/Schedule/UFC/2025"

    MMA_API_KEY = os.environ.get("MMA_API_KEY", None)
    assert MMA_API_KEY is not None, "Missing MMA API key"

    schedule_response = requests.get(schedule_url, params={"key": MMA_API_KEY})
    if schedule_response.status_code == 200:
        data = schedule_response.json()
        print(f"\nTotal fights retrieved: {len(data)}")
    else:
        print(f"Error: Received status code {schedule_response.status_code}")
        print(schedule_response.text)
        return {}

    fight_night_schedule = []
    ufc_schedule = []
    for fight in data:
        if not fight["DateTime"]:
            print(f"Skipping game with missing time: {fight}")
            continue

        date_formatted, time_formatted = UFC_timezone(fight["DateTime"])

        event_details_url = f"https://api.sportsdata.io/v3/mma/scores/json/Event/{fight['EventId']}"
        event_detail_response = requests.get(event_details_url, params={"key": MMA_API_KEY})
        if event_detail_response.status_code == 200:
            data = event_detail_response.json()
            print(f"\nTotal fighters retrieved: {len(data)}")
        else:
            print(f"Error: Received status code {event_detail_response.status_code}")
            print(event_detail_response.text)
            return {}
        
        description = "Scheduled Fights:\n\n"
        for fights in data["Fights"]:
            if fights["Fighters"]:
                fighter1_firstname = fights["Fighters"][0]["FirstName"] if fights["Fighters"][0]["FirstName"] else ""
                fighter1_lastname = fights["Fighters"][0]["LastName"] if fights["Fighters"][0]["LastName"] else ""
                fighter2_firstname = fights["Fighters"][1]["FirstName"] if fights["Fighters"][1]["FirstName"] else ""
                fighter2_lastname = fights["Fighters"][1]["LastName"] if fights["Fighters"][1]["LastName"] else ""

                description += f"{fighter1_firstname} {fighter1_lastname} vs {fighter2_firstname} {fighter2_lastname}\n"

        event = {
            "title": fight["Name"],
            "location": "",
            "date": date_formatted,
            "time": time_formatted,
            "description": description
        }

        if "Fight Night" in fight["Name"]:
            fight_night_schedule.append(event)
        else:
            ufc_schedule.append(event)

    return fight_night_schedule, ufc_schedule

def add_ufc_schedule_to_db(fight_night_schedule, ufc_schedule):
    calendar = {
        "name": "UFC Fight Nights",
        "events": fight_night_schedule,
        "organization": "UFC",
        "season": "2025"
    }
    _ = insert_calendar(calendar)

    calendar = {
        "name": "UFC",
        "events": ufc_schedule,
        "organization": "UFC",
        "season": "2025"
    }
    _ = insert_calendar(calendar)

if __name__ == "__main__":
    create_db_table()

    mlb_schedule = get_mlb_schedule()
    add_schedule_to_db(mlb_schedule, "MLB", "2025")

    nba_schedule = get_nba_schedule()
    add_schedule_to_db(nba_schedule, "NBA", "2024/2025")

    nfl_schedule = get_nfl_schedule()
    add_schedule_to_db(nfl_schedule, "NFL", "2024/2025")

    nhl_schedule = get_nhl_schedule()
    add_schedule_to_db(nhl_schedule, "NHL", "2024/2025")

    ipl_schedule = get_ipl_schedule()
    add_schedule_to_db(ipl_schedule, "IPL", "2025")

    top_soccer_leagues = {
        "MLS": "MLS",
        # "FIFA": "FIFA World Cup", # sportsdataio error...
        "UCL": "UEFA Champions League",
        "EPL": "Premier League",
        # "EUC": "European Championship", # sportsdataio error...
        "ESP": "La Liga",
        "DEB": "Bundesliga",
        "ITSA": "Serie A",
        
        # Tier 2: Major Competitions
        "FRL1": "Ligue 1",
        # "UEL": "UEFA Europa League",
        # "COPA": "Copa America", # sportsdataio error...
        # "BRSA": "Série A",
        # "ACN": "Africa Cup of Nations",
        # "RFPL": "RFPL",
        # "UCOL": "UEFA Europa Conference League",
        # "UNL": "UEFA Nations League",
        # "SPL": "Saudi Professional League"
    }

    for league_key, league_name in top_soccer_leagues.items():
        soccer_schedule = get_soccer_league_schedule(league_key)
        add_schedule_to_db(soccer_schedule, league_name, "2025", check_duplicates=True)

    fight_night_schedule, ufc_schedule = get_ufc_schedule()
    add_ufc_schedule_to_db(fight_night_schedule, ufc_schedule)