import argparse
from pathlib import Path

from conn import get_conn

# Creates the schema (safe to re-run). --reset drops every table first, including the old
# single-season tables (player_gameweek_stats, player_season_totals); data is re-loadable from
# the FPL API and vaastav.

ALL_TABLES = ["player_gameweek_stats", "player_season_totals", "player_fixture_stats", "ep_snapshots",
              "fixtures", "gameweeks", "players", "teams", "positions", "ingest_runs"]

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="drop all tables before creating them")
args = parser.parse_args()

conn = get_conn()
cur = conn.cursor()

if args.reset:
    for table in ALL_TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
    print("Dropped existing tables")
else:
    # CREATE TABLE IF NOT EXISTS would silently keep the old players table, so refuse instead
    cur.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'players'
          AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'players' AND column_name = 'season')
    """)
    if cur.fetchone():
        raise SystemExit("Found the old single-season schema. Run `python src/db/init_db.py --reset` once.")

cur.execute((Path(__file__).parent / "schema.sql").read_text())
conn.commit()
cur.close()
conn.close()
print("Schema ready")
