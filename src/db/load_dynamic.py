import os
from datetime import datetime

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

today = datetime.today()
if today.month >= 8:  # New season starts in August
    current_season = f"{today.year}/{str(today.year+1)[-2:]}"
else:
    current_season = f"{today.year-1}/{str(today.year)[-2:]}"
print(f" Current season: {current_season}")


load_dotenv()
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

print(f"Connecting to {HOST}:{PORT}/{DBNAME} as {USER}")

conn = psycopg2.connect(
    user=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT,
    dbname=DBNAME,
    sslmode="require"
)
cur = conn.cursor()
print("Connection successful")

# Preload bootstrap data for market data
print("Fetching bootstrap-static for market data")
bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
players_market = {
    p["id"]: {
        "now_cost": p["now_cost"],
        "selected_by_percent": p["selected_by_percent"],
        "transfers_in_event": p["transfers_in_event"],
        "transfers_out_event": p["transfers_out_event"],
    }
    for p in bootstrap["elements"]
}
print(f"Loaded {len(players_market)} players market data.")


for gw in range(1, 39):  # max 38 GWs
    print(f"\n📦 Fetching data for GW {gw}...")
    url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"
    res = requests.get(url)
    data = res.json()

    if "elements" not in data or len(data["elements"]) == 0:
        print(f" GW {gw} not available yet.")
        break

    player_stats = []
    for details in data["elements"]:
        player_id = details["id"]
        stats = details["stats"]

        # merge match stats + market stats
        market = players_market.get(player_id, {})
        player_stats.append((
            int(player_id),current_season, gw,
            stats["minutes"], stats["goals_scored"], stats["assists"],
            stats["clean_sheets"], stats["goals_conceded"], stats["own_goals"],
            stats["penalties_saved"], stats["penalties_missed"], stats["yellow_cards"],
            stats["red_cards"], stats["saves"], stats["bonus"], stats["bps"],
            stats["influence"], stats["creativity"], stats["threat"], stats["ict_index"],
            stats["total_points"],
            market.get("now_cost"),
            market.get("selected_by_percent"),
            market.get("transfers_in_event"),
            market.get("transfers_out_event")
        ))


    def ensure_columns(cur, table, expected_cols):
        for col, dtype in expected_cols.items():
            cur.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, col))

            if cur.fetchone() is None:
                print(f"Adding missing column: {col} {dtype}")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype};")


    expected_columns = {
        "player_id": "INT",
        "season": "TEXT",
        "gameweek": "INT",
        "minutes": "INT",
        "total_points": "INT",
        "goals_scored": "INT",
        "assists": "INT",
        "clean_sheets": "INT",
        "goals_conceded": "INT",
        "own_goals": "INT",
        "penalties_saved": "INT",
        "penalties_missed": "INT",
        "yellow_cards": "INT",
        "red_cards": "INT",
        "saves": "INT",
        "bonus": "INT",
        "bps": "INT",
        "influence": "NUMERIC",
        "creativity": "NUMERIC",
        "threat": "NUMERIC",
        "ict_index": "NUMERIC",
        "now_cost": "INT",
        "selected_by_percent": "NUMERIC",
        "transfers_in": "INT",
        "transfers_out": "INT"
    }
    ensure_columns(cur,'player_gameweek_stats', expected_columns)

    print(f"Inserting {len(player_stats)} rows for GW {gw}")
    execute_values(cur, """
        INSERT INTO player_gameweek_stats (
            player_id, season, gameweek, minutes, goals_scored, assists,
            clean_sheets, goals_conceded, own_goals, penalties_saved,
            penalties_missed, yellow_cards, red_cards, saves, bonus, bps,
            influence, creativity, threat, ict_index, total_points,
            now_cost, selected_by_percent, transfers_in, transfers_out
        )
        VALUES %s
        ON CONFLICT (player_id, season, gameweek) DO UPDATE SET
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
            now_cost = EXCLUDED.now_cost,
            selected_by_percent = EXCLUDED.selected_by_percent,
            transfers_in = EXCLUDED.transfers_in,
            transfers_out = EXCLUDED.transfers_out;
    """, player_stats)

    conn.commit()
    print(f"GW {gw} stats inserted/updated.")

cur.close()
conn.close()
print("\nAll available gameweeks processed!")