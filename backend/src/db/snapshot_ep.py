import sys
from datetime import datetime, timezone

import requests

from conn import get_conn
from ingest import ingest_run, season_label, upsert

# Saves FPL's own expected points (ep_next) for the upcoming gameweek. FPL overwrites ep_next once
# the deadline passes, so this has to run before every deadline (e.g. daily); each run replaces the
# previous snapshot for that gameweek, so the stored one is the latest taken before the deadline.
# This is the FPL-xP baseline for the live season (past seasons have xp from vaastav).

bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=30).json()
events = bootstrap["events"]
season = season_label(int(events[0]["deadline_time"][:4]))

upcoming = next((e for e in events if e["is_next"]), None)
if upcoming is None:
    print("No upcoming gameweek, nothing to snapshot")
    sys.exit(0)  # not an error, e.g. end of season

now = datetime.now(timezone.utc)
deadline = datetime.fromisoformat(upcoming["deadline_time"].replace("Z", "+00:00"))
if now >= deadline:
    print(f"GW{upcoming['id']} deadline has passed, not snapshotting")
    sys.exit(0)


def number(value):
    return float(value) if value not in (None, "") else None


rows = [(season, upcoming["id"], p["id"], now, number(p["ep_next"]), number(p["ep_this"]),
         p["chance_of_playing_next_round"], p["status"], p["now_cost"], number(p["selected_by_percent"]))
        for p in bootstrap["elements"]]

conn = get_conn()
cur = conn.cursor()
with ingest_run(conn, "ep_snapshot", season) as run:
    run["rows"] = upsert(cur, "ep_snapshots",
                         ["season", "gameweek", "player_id", "taken_at", "ep_next", "ep_this",
                          "chance_of_playing_next_round", "status", "now_cost", "selected_by_percent"],
                         rows, ["season", "gameweek", "player_id"])
    run["gameweeks"] = [upcoming["id"]]
cur.close()
conn.close()
print(f"Saved ep_next for GW{upcoming['id']} ({len(rows)} players), {deadline - now} before the deadline")
