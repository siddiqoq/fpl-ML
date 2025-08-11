from dotenv import load_dotenv
import os
import requests
import psycopg2
from psycopg2.extras import execute_values

# .env should look like this
# user=postgres.eqpijwihquslkstwound
# password=
# host=aws-0-us-east-2.pooler.supabase.com
# port=5432
# dbname=postgres

# --- Load env variables ---
load_dotenv()
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

print(f"Connecting to {HOST}:{PORT}/{DBNAME} as {USER}...")

# --- Connect to Supabase Postgres ---
conn = psycopg2.connect(
    user=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT,
    dbname=DBNAME,
    sslmode="require"
)
cur = conn.cursor()
print("Connection successful!")

# --- Fetch FPL bootstrap data ---
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
print(f"Fetching data from {url}...")
data = requests.get(url).json()
print("Data fetched successfully.")

# --- Positions ---
print("Preparing positions data...")
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

# --- Players ---
print("Preparing players data...")
players_data = [
    (
        p["id"], p["first_name"], p["second_name"], p["web_name"],
        p["element_type"], p["team"], p["code"]
    )
    for p in data["elements"]
]
print(f"Players rows: {len(players_data)}")

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
print("Players inserted/updated.")

# --- Commit and close ---
conn.commit()
cur.close()
conn.close()
print("Static data loaded successfully in bulk mode!")
