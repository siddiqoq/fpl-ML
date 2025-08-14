from dotenv import load_dotenv
import os
import requests
import psycopg2
import time
from psycopg2.extras import execute_values

# Stores every gw stat in the player_gameweek_stats for current season and updates season total
# Run after each gameweek has finished

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

# STORE STATS FOR EACH PLAYER IN THE CURRENT GW
for gw in range(1, 39):  # FPL usually has 38 GWs
    print(f"\n📦 Fetching data for GW {gw}...")
    url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"
    res = requests.get(url)

    if res.status_code != 200:
        print(f"⚠️ GW {gw} not available yet. Skipping.")
        continue

    data = res.json()
    print(data)
    player_stats = []

    for details in data["elements"]:
        player_id = details["id"]
        stats = details["stats"]

        print(player_id)
        print('test')
        player_stats.append((
            int(player_id), gw,
            stats["minutes"], stats["goals_scored"], stats["assists"],
            stats["clean_sheets"], stats["goals_conceded"], stats["own_goals"],
            stats["penalties_saved"], stats["penalties_missed"], stats["yellow_cards"],
            stats["red_cards"], stats["saves"], stats["bonus"], stats["bps"],
            stats["influence"], stats["creativity"], stats["threat"], stats["ict_index"],
            stats["total_points"], stats["value"], stats["selected_by_percent"],
            stats["transfers_in"], stats["transfers_out"]
        ))

    # Insert into DB
    cur.executemany("""
        INSERT INTO player_gameweek_stats (
            player_id, gameweek, minutes, goals_scored, assists, clean_sheets,
            goals_conceded, own_goals, penalties_saved, penalties_missed,
            yellow_cards, red_cards, saves, bonus, bps,
            influence, creativity, threat, ict_index,
            total_points, value, selected_by_percent, transfers_in, transfers_out
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (player_id, gameweek) DO UPDATE SET
            minutes = EXCLUDED.minutes,
            goals_scored = EXCLUDED.goals_scored,
            assists = EXCLUDED.assists,
            clean_sheets = EXCLUDED.clean_sheets,
            goals_conceded = EXCLUDED.goals_conceded,
            own_goals = EXCLUDED.own_goals,
            penalties_saved = EXCLUDED.penalties_saved,
            penalties_missed = EXCLUDED.penalties_missed,
            yellow_cards = EXCLUDED.yellow_cards,
            red_cards = EXCLUDED.red_cards,
            saves = EXCLUDED.saves,
            bonus = EXCLUDED.bonus,
            bps = EXCLUDED.bps,
            influence = EXCLUDED.influence,
            creativity = EXCLUDED.creativity,
            threat = EXCLUDED.threat,
            ict_index = EXCLUDED.ict_index,
            total_points = EXCLUDED.total_points,
            value = EXCLUDED.value,
            selected_by_percent = EXCLUDED.selected_by_percent,
            transfers_in = EXCLUDED.transfers_in,
            transfers_out = EXCLUDED.transfers_out;
    """, player_stats)

    conn.commit()
    print(f"✅ GW {gw} data inserted/updated successfully.")
    time.sleep(1)  # Avoid hammering the API

# --- Aggregate into player_season_totals ---
print("📊 Aggregating season totals...")
cur.execute("""
    SELECT 
        player_id,
        season,
        SUM(minutes) AS minutes,
        SUM(total_points) AS total_points,
        SUM(goals_scored) AS goals_scored,
        SUM(assists) AS assists,
        SUM(clean_sheets) AS clean_sheets,
        SUM(goals_conceded) AS goals_conceded,
        SUM(saves) AS saves,
        SUM(yellow_cards) AS yellow_cards,
        SUM(red_cards) AS red_cards
    FROM player_gameweek_stats
    GROUP BY player_id, season
""")
totals = cur.fetchall()

insert_query = """
INSERT INTO player_season_totals (
    player_id, season, minutes, total_points, goals_scored,
    assists, clean_sheets, goals_conceded, saves,
    yellow_cards, red_cards
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
"""

execute_values(cur, insert_query, totals)
print(f"✅ Updated {len(totals)} season total records.")

# --- Commit and close ---
conn.commit()
cur.close()
conn.close()
print("🏁 Dynamic data + season totals update complete.")