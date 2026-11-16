import argparse
import time

import pandas as pd
import requests

from conn import get_conn
from ingest import (FIXTURE_COLUMNS, FIXTURE_STAT_COLUMNS, GAMEWEEK_COLUMNS, PLAYER_COLUMNS, TEAM_COLUMNS,
                    add_player_team, ingest_run, report_duplicates, season_label, upsert, upsert_df)

# Loads the live season from the FPL API. Only gameweeks FPL marks finished AND data_checked are
# loaded (stats can still change before that), and gameweeks already in the DB are skipped unless
# --reload is passed. Per-fixture stats come from each player's element-summary history, which
# has the same columns as vaastav, including that gameweek's price and ownership.

API = "https://fantasy.premierleague.com/api"

parser = argparse.ArgumentParser()
parser.add_argument("--reload", action="store_true", help="re-fetch every completed gameweek")
args = parser.parse_args()

session = requests.Session()


def get(path):
    res = session.get(f"{API}/{path}", timeout=30)
    res.raise_for_status()
    return res.json()


bootstrap = get("bootstrap-static/")
events = bootstrap["events"]
season = season_label(int(events[0]["deadline_time"][:4]))
print(f"Season {season}")

teams = pd.DataFrame(bootstrap["teams"]).rename(columns={"id": "team_id"}).assign(season=season)
players = pd.DataFrame(bootstrap["elements"]).rename(columns={"id": "player_id", "team": "team_id"}).assign(season=season)
gameweeks = pd.DataFrame(events).rename(columns={"id": "gameweek"}).assign(season=season)
fixtures = pd.DataFrame(get("fixtures/")).rename(columns={"id": "fixture_id", "event": "gameweek"}).assign(season=season)
positions = [(p["id"], p["singular_name"], p["plural_name"]) for p in bootstrap["element_types"]]

complete = [e["id"] for e in events if e["finished"] and e["data_checked"]]

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT DISTINCT gameweek FROM player_fixture_stats WHERE season = %s", (season,))
loaded = {row[0] for row in cur.fetchall()}
todo = complete if args.reload else sorted(set(complete) - loaded)

with ingest_run(conn, "fpl_api", season) as run:
    upsert(cur, "positions", ["element_type", "singular_name", "plural_name"], positions, ["element_type"])
    upsert_df(cur, "teams", TEAM_COLUMNS, teams, ["season", "team_id"])
    upsert_df(cur, "players", PLAYER_COLUMNS, players, ["season", "player_id"])
    upsert_df(cur, "gameweeks", GAMEWEEK_COLUMNS, gameweeks, ["season", "gameweek"])
    upsert_df(cur, "fixtures", FIXTURE_COLUMNS, fixtures, ["season", "fixture_id"])

    if todo:
        print(f"Fetching GWs {todo} for {len(players)} players (about 2-3 minutes)")
        history = []
        for i, player_id in enumerate(players["player_id"], start=1):
            rows = get(f"element-summary/{player_id}/")["history"]
            history.extend(r for r in rows if r["round"] in todo)
            if i % 100 == 0:
                print(f"  {i}/{len(players)} players")
            time.sleep(0.1)  # be gentle with the FPL API

        stats = pd.DataFrame(history).rename(columns={"element": "player_id", "fixture": "fixture_id",
                                                      "round": "gameweek"})
        stats = add_player_team(stats.assign(season=season), fixtures)
        stats = report_duplicates(stats, ["player_id", "fixture_id"], "player-fixture")
        run["rows"] = upsert_df(cur, "player_fixture_stats", FIXTURE_STAT_COLUMNS, stats,
                                ["season", "player_id", "fixture_id"])
    run["gameweeks"] = todo

if todo:
    print(f"Loaded GWs {todo}: {run['rows']} player-fixture rows")
else:
    print(f"No new completed gameweeks (loaded: {sorted(loaded) or 'none'})")
cur.close()
conn.close()
