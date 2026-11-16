import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from ingest import EP_SNAPSHOT_COLUMNS, EP_SNAPSHOT_KEY, NEWER_SNAPSHOT, ingest_run, season_label, upsert

# Saves FPL's own expected points (ep_next) for the upcoming gameweek. FPL overwrites ep_next once
# the deadline passes, so a missed snapshot can't be recovered; each run replaces the previous
# snapshot for that gameweek, so the stored one is the latest taken before the deadline.
# This is the FPL-xP baseline for the live season (past seasons have xp from vaastav).
#   python src/db/snapshot_ep.py        -> writes to Postgres
#   python src/db/snapshot_ep.py --csv  -> writes backend/data/ep_snapshots/<season>/gwNN.csv instead
# The --csv mode is what the GitHub Action (.github/workflows/ep-snapshot.yml) runs, so snapshots
# keep being taken when this machine is off; load_current.py imports the CSVs into Postgres.

SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "ep_snapshots"

parser = argparse.ArgumentParser()
parser.add_argument("--csv", action="store_true", help=f"write to {SNAPSHOT_DIR} instead of the DB")
args = parser.parse_args()

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

if args.csv:
    path = SNAPSHOT_DIR / season.replace("/", "-") / f"gw{upcoming['id']:02d}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(EP_SNAPSHOT_COLUMNS)
        writer.writerows((*row[:3], now.isoformat(), *row[4:]) for row in rows)
    where = path
else:
    from conn import get_conn  # only the DB mode needs a database

    conn = get_conn()
    cur = conn.cursor()
    with ingest_run(conn, "ep_snapshot", season) as run:
        run["rows"] = upsert(cur, "ep_snapshots", EP_SNAPSHOT_COLUMNS, rows, EP_SNAPSHOT_KEY, NEWER_SNAPSHOT)
        run["gameweeks"] = [upcoming["id"]]
    cur.close()
    conn.close()
    where = "the DB"
print(f"Saved ep_next for GW{upcoming['id']} ({len(rows)} players) to {where}, {deadline - now} before the deadline")
