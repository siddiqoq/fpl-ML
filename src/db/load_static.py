from dotenv import load_dotenv
import os
import requests
import psycopg2
from psycopg2.extras import execute_values
import time
from datetime import (datetime)
from pathlib import Path
from dotenv import load_dotenv

# .env should look like this
# user=postgres.eqpijwihquslkstwound
# password=
# host=aws-0-us-east-2.pooler.supabase.com
# port=5432
# dbname=postgres

# This script runs static data, you only need to run it once unless there are player transfers / fixture delays

# FPL's official archive only stores data from 2016/17 onwards and
# past seasons only have end of season total data

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)
print("Looking for .env at:", env_path)
print("Exists?", env_path.exists())

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("name")

print(f"Connecting to {HOST}:{PORT}/{DBNAME} as {USER}...")

# --- Connect to Supabase Postgres ---
conn = psycopg2.connect(
    user=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT,
    dbname=DBNAME,
    sslmode=os.getenv("DB_SSLMODE", "disable")
)
cur = conn.cursor()
print("Connection successful!")

#Fetch FPL bootstrap data
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
print(f"Fetching data from {url}")
data = requests.get(url).json()
print("Data fetched successfully.")

#Positions
print("Preparing positions data")

cur.execute("""CREATE TABLE IF NOT EXISTS positions (
    element_type INT PRIMARY KEY,
    singular_name TEXT NOT NULL,
    plural_name TEXT NOT NULL
);""")
positions_data = [
    (p["id"], p["singular_name"], p["plural_name"])
    for p in data["element_types"]
]
print(f"Positions rows: {len(positions_data)}")

execute_values(cur, """
    INSERT INTO positions (element_type, singular_name, plural_name)
    VALUES %s
    ON CONFLICT (element_type) DO UPDATE 
    SET singular_name = EXCLUDED.singular_name,
        plural_name = EXCLUDED.plural_name;
""", positions_data)
print("Positions inserted/updated.")

# --- Teams ---
print("Preparing teams data...")
cur.execute("""CREATE TABLE IF NOT EXISTS teams (
    team_id INT PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    strength_overall_home INT,
    strength_overall_away INT,
    strength_attack_home INT,
    strength_attack_away INT,
    strength_defence_home INT,
    strength_defence_away INT
);""")
teams_data = [
    (
        t["id"], t["name"], t["short_name"],
        t["strength_overall_home"], t["strength_overall_away"],
        t["strength_attack_home"], t["strength_attack_away"],
        t["strength_defence_home"], t["strength_defence_away"]
    )
    for t in data["teams"]
]
print(f"Teams rows: {len(teams_data)}")

execute_values(cur, """
    INSERT INTO teams (team_id, name, short_name, strength_overall_home, strength_overall_away,
                       strength_attack_home, strength_attack_away, strength_defence_home, strength_defence_away)
    VALUES %s
    ON CONFLICT (team_id) DO UPDATE SET
        name = EXCLUDED.name,
        short_name = EXCLUDED.short_name,
        strength_overall_home = EXCLUDED.strength_overall_home,
        strength_overall_away = EXCLUDED.strength_overall_away,
        strength_attack_home = EXCLUDED.strength_attack_home,
        strength_attack_away = EXCLUDED.strength_attack_away,
        strength_defence_home = EXCLUDED.strength_defence_home,
        strength_defence_away = EXCLUDED.strength_defence_away;
""", teams_data)
print("Teams inserted/updated.")

# Fixtures
url = "https://fantasy.premierleague.com/api/fixtures/"
print(f" Fetching fixtures from {url} ...")
fixtures = requests.get(url).json()
print(f" Total fixtures fetched: {len(fixtures)}")

today = datetime.today()
if today.month >= 8:  # New season starts in August
    current_season = f"{today.year}/{str(today.year+1)[-2:]}"
else:
    current_season = f"{today.year-1}/{str(today.year)[-2:]}"
print(f" Current season: {current_season}")

# Prepare fixture data
cur.execute("""CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id INT PRIMARY KEY,
    season TEXT NOT NULL,
    gameweek INT,
    kickoff_time TIMESTAMP,
    team_h INT REFERENCES teams(team_id),
    team_a INT REFERENCES teams(team_id),
    team_h_score INT,
    team_a_score INT,
    finished BOOLEAN DEFAULT FALSE
);""")
fixtures_data = []
for f in fixtures:
    fixtures_data.append((
        f["id"],
        current_season,
        f.get("event"),  # gameweek
        f.get("kickoff_time"),
        f.get("team_h"),
        f.get("team_a"),
        f.get("team_h_score"),
        f.get("team_a_score"),
        f.get("finished", False)
    ))

print(f" Rows prepared: {len(fixtures_data)}")

# Insert/update fixtures
execute_values(cur, """
    INSERT INTO fixtures (
        fixture_id, season, gameweek, kickoff_time,
        team_h, team_a, team_h_score, team_a_score, finished
    )
    VALUES %s
    ON CONFLICT (fixture_id) DO UPDATE SET
        season = EXCLUDED.season,
        gameweek = EXCLUDED.gameweek,
        kickoff_time = EXCLUDED.kickoff_time,
        team_h = EXCLUDED.team_h,
        team_a = EXCLUDED.team_a,
        team_h_score = EXCLUDED.team_h_score,
        team_a_score = EXCLUDED.team_a_score,
        finished = EXCLUDED.finished;
""", fixtures_data)


# Players + Season Totals
players_data = []
season_totals_data = []

print(" Fetching player season totals (per-player requests)...")
for idx, p in enumerate(data["elements"], start=1):
    players_data.append((
        p["id"], p["first_name"], p["second_name"], p["web_name"],
        p["element_type"], p["team"], p["code"]
    ))

    # Fetch per-player history
    detail_url = f"https://fantasy.premierleague.com/api/element-summary/{p['id']}/"
    r = requests.get(detail_url)
    if r.status_code == 200:
        history_past = r.json().get("history_past", [])
        for season_stat in history_past:
            season_totals_data.append((
                p["id"],
                season_stat["season_name"],
                season_stat.get("minutes", 0),
                season_stat.get("total_points", 0),
                season_stat.get("goals_scored", 0),
                season_stat.get("assists", 0),
                season_stat.get("clean_sheets", 0),
                season_stat.get("goals_conceded", 0),
                season_stat.get("saves", 0),
                season_stat.get("yellow_cards", 0),
                season_stat.get("red_cards", 0)
            ))
    else:
        print(f"️ Failed to fetch history for player {p['id']}")

    if idx % 50 == 0:
        print(f"   Processed {idx}/{len(data['elements'])} players...")
    time.sleep(0.2)  # Be nice to FPL API

cur.execute("""CREATE TABLE IF NOT EXISTS players (
    player_id INT PRIMARY KEY,
    first_name TEXT NOT NULL,
    second_name TEXT NOT NULL,
    web_name TEXT NOT NULL,
    element_type INT REFERENCES positions(element_type),
    team_id INT REFERENCES teams(team_id),
    code INT
);""")
# Insert players
execute_values(cur, """
    INSERT INTO players (player_id, first_name, second_name, web_name, element_type, team_id, code)
    VALUES %s
    ON CONFLICT (player_id) DO UPDATE SET
        first_name = EXCLUDED.first_name,
        second_name = EXCLUDED.second_name,
        web_name = EXCLUDED.web_name,
        element_type = EXCLUDED.element_type,
        team_id = EXCLUDED.team_id,
        code = EXCLUDED.code;
""", players_data)
print(f" Players inserted/updated: {len(players_data)}")

# Insert season totals
cur.execute("""CREATE TABLE IF NOT EXISTS player_season_totals (
    player_id INT REFERENCES players(player_id),
    season TEXT NOT NULL,
    minutes INT DEFAULT 0,
    total_points INT DEFAULT 0,
    goals_scored INT DEFAULT 0,
    assists INT DEFAULT 0,
    clean_sheets INT DEFAULT 0,
    goals_conceded INT DEFAULT 0,
    saves INT DEFAULT 0,
    yellow_cards INT DEFAULT 0,
    red_cards INT DEFAULT 0,
    PRIMARY KEY (player_id, season)
);""")

if season_totals_data:
    execute_values(cur, """
        INSERT INTO player_season_totals (
            player_id, season, minutes, total_points, goals_scored, assists,
            clean_sheets, goals_conceded, saves, yellow_cards, red_cards
        )
        VALUES %s
        ON CONFLICT (player_id, season) DO UPDATE SET
            minutes = EXCLUDED.minutes,
            total_points = EXCLUDED.total_points,
            goals_scored = EXCLUDED.goals_scored,
            assists = EXCLUDED.assists,
            clean_sheets = EXCLUDED.clean_sheets,
            goals_conceded = EXCLUDED.goals_conceded,
            saves = EXCLUDED.saves,
            yellow_cards = EXCLUDED.yellow_cards,
            red_cards = EXCLUDED.red_cards;
    """, season_totals_data)
print(f" Player season totals inserted/updated: {len(season_totals_data)}")

cur.execute("""CREATE TABLE IF NOT EXISTS player_gameweek_stats (
    player_id INT REFERENCES players(player_id),
    season TEXT NOT NULL,
    gameweek INT NOT NULL,
    minutes INT DEFAULT 0,
    goals_scored INT DEFAULT 0,
    assists INT DEFAULT 0,
    clean_sheets INT DEFAULT 0,
    goals_conceded INT DEFAULT 0,
    own_goals INT DEFAULT 0,
    penalties_saved INT DEFAULT 0,
    penalties_missed INT DEFAULT 0,
    yellow_cards INT DEFAULT 0,
    red_cards INT DEFAULT 0,
    saves INT DEFAULT 0,
    bonus INT DEFAULT 0,
    bps INT DEFAULT 0,
    influence NUMERIC DEFAULT 0,
    creativity NUMERIC DEFAULT 0,
    threat NUMERIC DEFAULT 0,
    ict_index NUMERIC DEFAULT 0,
    total_points INT DEFAULT 0,
    now_cost INT DEFAULT 0,
    selected_by_percent NUMERIC DEFAULT 0,
    transfers_in INT DEFAULT 0,
    transfers_out INT DEFAULT 0,
    PRIMARY KEY (player_id, season, gameweek)
);""")

conn.commit()
cur.close()
conn.close()
print(" Static + season totals data loaded successfully!")