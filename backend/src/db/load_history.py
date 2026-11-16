import sys
from pathlib import Path

import pandas as pd
import requests

from conn import get_conn
from ingest import (FIXTURE_COLUMNS, FIXTURE_STAT_COLUMNS, GAMEWEEK_COLUMNS, PLAYER_COLUMNS, TEAM_COLUMNS,
                    add_player_team, ingest_run, report_duplicates, season_label, upsert_df)

# Loads completed past seasons from github.com/vaastav/Fantasy-Premier-League (the FPL API only
# serves the current season). Run once per season; re-running is safe.
#   python src/db/load_history.py                 -> every season 2016-17 .. 2025-26
#   python src/db/load_history.py 2024-25 2025-26 -> just those seasons
# Downloads are cached in backend/data/raw/vaastav/.

BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "vaastav"
DEFAULT_SEASONS = [f"{y}-{(y + 1) % 100:02d}" for y in range(2016, 2026)]


def fetch_csv(path):
    # returns None if vaastav doesn't have the file for that season
    local = CACHE_DIR / path
    if not local.exists():
        res = requests.get(f"{BASE_URL}/{path}", timeout=60)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(res.content)
    try:
        return pd.read_csv(local, low_memory=False)
    except UnicodeDecodeError:  # some early files aren't UTF-8
        return pd.read_csv(local, encoding="latin-1", low_memory=False)


def build_teams(folder, season, fixtures):
    teams = fetch_csv(f"{folder}/teams.csv")
    if teams is not None:
        return teams.rename(columns={"id": "team_id"}).assign(season=season)
    # teams.csv only exists from 2019-20; earlier seasons only have names
    master = fetch_csv("master_team_list.csv")
    teams = master[master["season"] == folder].rename(columns={"team": "team_id", "team_name": "name"})
    if teams.empty:
        raise ValueError(f"No team list for {folder}")
    return teams.assign(season=season)


def build_fixtures(folder, season, gws):
    fixtures = fetch_csv(f"{folder}/fixtures.csv")
    if fixtures is not None:
        return fixtures.rename(columns={"id": "fixture_id", "event": "gameweek"}).assign(season=season)
    # 2016-17 and 2017-18 have no fixtures.csv: rebuild from match rows, where an away player's
    # opponent is the home side and vice versa
    home_rows = gws[gws["was_home"]].groupby("fixture").first()
    away_rows = gws[~gws["was_home"]].groupby("fixture").first()
    fixtures = pd.DataFrame({
        "team_h": away_rows["opponent_team"],
        "team_a": home_rows["opponent_team"],
    })
    first_row = gws.groupby("fixture").first()
    fixtures["gameweek"] = first_row["GW"]
    fixtures["kickoff_time"] = first_row["kickoff_time"]
    fixtures["team_h_score"] = first_row["team_h_score"]
    fixtures["team_a_score"] = first_row["team_a_score"]
    fixtures["finished"] = True
    return fixtures.rename_axis("fixture_id").reset_index().assign(season=season)


def load_season(conn, folder):
    season = season_label(int(folder[:4]))
    print(f"\n{season}")
    gws = fetch_csv(f"{folder}/gws/merged_gw.csv")
    players = fetch_csv(f"{folder}/players_raw.csv")
    if gws is None or players is None:
        raise ValueError(f"vaastav has no merged_gw.csv/players_raw.csv for {folder}")

    fixtures = build_fixtures(folder, season, gws)
    teams = build_teams(folder, season, fixtures)
    players = players.rename(columns={"id": "player_id", "team": "team_id"}).assign(season=season)
    gameweeks = pd.DataFrame({"gameweek": sorted(gws["GW"].unique())}).assign(
        season=season, finished=True, data_checked=True)

    stats = gws.rename(columns={"element": "player_id", "fixture": "fixture_id", "GW": "gameweek", "xP": "xp"})
    stats = add_player_team(stats.assign(season=season), fixtures)

    # A postponed match can appear twice: a stale 0-minute row in its original GW and the real one in
    # the GW it was played (e.g. 2019/20 fixture 275). Keep the row whose GW matches the fixture's.
    fixture_gw = stats["fixture_id"].map(fixtures.set_index("fixture_id")["gameweek"])
    stale = stats.duplicated(["player_id", "fixture_id"], keep=False) & (stats["gameweek"] != fixture_gw)
    if stale.any():
        print(f"  Dropped {stale.sum()} stale rows for postponed fixtures")
    stats = report_duplicates(stats[~stale], ["player_id", "fixture_id"], "player-fixture")

    # vaastav stores xP as 0 for every player in gameweeks it didn't capture: that's missing, not 0
    xp_missing_gws = []
    if "xp" in stats.columns:
        all_zero = stats.groupby("gameweek")["xp"].transform(lambda s: s.fillna(0).eq(0).all())
        xp_missing_gws = sorted(int(g) for g in stats.loc[all_zero, "gameweek"].unique())
        stats.loc[all_zero, "xp"] = None
        if xp_missing_gws:
            print(f"  xP missing (all zero) in GWs {xp_missing_gws}, stored as NULL")

    cur = conn.cursor()
    with ingest_run(conn, "vaastav", season) as run:
        upsert_df(cur, "teams", TEAM_COLUMNS, teams, ["season", "team_id"])
        upsert_df(cur, "players", PLAYER_COLUMNS, players, ["season", "player_id"])
        upsert_df(cur, "gameweeks", GAMEWEEK_COLUMNS, gameweeks, ["season", "gameweek"])
        upsert_df(cur, "fixtures", FIXTURE_COLUMNS, fixtures, ["season", "fixture_id"])
        run["rows"] = upsert_df(cur, "player_fixture_stats", FIXTURE_STAT_COLUMNS, stats,
                                ["season", "player_id", "fixture_id"])
        run["gameweeks"] = gameweeks["gameweek"].tolist()

        missing = [c for c in FIXTURE_STAT_COLUMNS if c not in stats.columns]
        notes = []
        if missing:
            notes.append(f"not recorded this season (stored as NULL): {', '.join(missing)}")
        if xp_missing_gws:
            notes.append(f"xp missing in GWs {xp_missing_gws}")
        run["message"] = "; ".join(notes) or None

    print(f"  {len(teams)} teams, {len(players)} players, {len(fixtures)} fixtures, "
          f"{len(gameweeks)} GWs, {run['rows']} player-fixture rows (merged_gw has {len(gws)})")
    if missing:
        print(f"  NULL columns: {', '.join(missing)}")
    cur.close()


seasons = sys.argv[1:] or DEFAULT_SEASONS
conn = get_conn()
for folder in seasons:
    load_season(conn, folder)
conn.close()
print("\nHistory loaded")
