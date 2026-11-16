from contextlib import contextmanager

from psycopg2.extras import execute_values

# Per-fixture columns shared by vaastav's merged_gw.csv and the API's element-summary history
STAT_COLUMNS = [
    "minutes", "starts", "total_points", "goals_scored", "assists", "clean_sheets", "goals_conceded",
    "own_goals", "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus",
    "bps", "influence", "creativity", "threat", "ict_index", "expected_goals", "expected_assists",
    "expected_goal_involvements", "expected_goals_conceded", "defensive_contribution",
    "clearances_blocks_interceptions", "recoveries", "tackles", "value", "selected", "transfers_in",
    "transfers_out", "transfers_balance",
]
FIXTURE_STAT_COLUMNS = (["season", "player_id", "fixture_id", "gameweek", "kickoff_time", "team_id",
                         "opponent_team", "was_home"] + STAT_COLUMNS + ["xp"])

TEAM_COLUMNS = ["season", "team_id", "code", "name", "short_name", "strength_overall_home",
                "strength_overall_away", "strength_attack_home", "strength_attack_away",
                "strength_defence_home", "strength_defence_away"]
PLAYER_COLUMNS = ["season", "player_id", "code", "first_name", "second_name", "web_name",
                  "element_type", "team_id"]
FIXTURE_COLUMNS = ["season", "fixture_id", "gameweek", "kickoff_time", "team_h", "team_a",
                   "team_h_score", "team_a_score", "team_h_difficulty", "team_a_difficulty", "finished"]
GAMEWEEK_COLUMNS = ["season", "gameweek", "deadline_time", "finished", "data_checked"]


def season_label(year_start):
    # 2025 -> '2025/26', the format stored in every table
    return f"{year_start}/{(year_start + 1) % 100:02d}"


def add_player_team(stats, fixtures):
    # a player's team in a match is the home side if they were at home, otherwise the away side
    teams = fixtures[["fixture_id", "team_h", "team_a"]]
    stats = stats.merge(teams, on="fixture_id", how="left")
    stats["team_id"] = stats["team_h"].where(stats["was_home"], stats["team_a"])
    return stats.drop(columns=["team_h", "team_a"])


def to_rows(df, columns):
    # missing columns become NULL (not 0); numpy scalars become plain Python values for psycopg2
    df = df.reindex(columns=columns).astype(object)
    df = df.where(df.notna(), None)
    return [tuple(v.item() if hasattr(v, "item") else v for v in row) for row in df.itertuples(index=False)]


def upsert(cur, table, columns, rows, key):
    if not rows:
        return 0
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c not in key)
    execute_values(cur, f"""
        INSERT INTO {table} ({", ".join(columns)}) VALUES %s
        ON CONFLICT ({", ".join(key)}) DO UPDATE SET {updates}
    """, rows, page_size=2000)
    return len(rows)


def upsert_df(cur, table, columns, df, key):
    return upsert(cur, table, columns, to_rows(df, columns), key)


@contextmanager
def ingest_run(conn, source, season=None):
    # logs the load to ingest_runs; the caller's writes are committed only if the block succeeds
    cur = conn.cursor()
    cur.execute("INSERT INTO ingest_runs (source, season, status) VALUES (%s, %s, 'running') RETURNING run_id",
                (source, season))
    run_id = cur.fetchone()[0]
    conn.commit()
    run = {"gameweeks": [], "rows": 0, "message": None}
    try:
        yield run
        conn.commit()
        status, message = "ok", run["message"]
    except Exception as e:
        conn.rollback()
        status, message = "failed", str(e)
        raise
    finally:
        cur.execute("""
            UPDATE ingest_runs SET finished_at = now(), status = %s, message = %s,
                   gameweeks = %s, rows_written = %s
            WHERE run_id = %s
        """, (status, message, [int(g) for g in run["gameweeks"]], run["rows"], run_id))
        conn.commit()


def report_duplicates(df, key, what):
    dupes = df.duplicated(subset=key, keep="last")
    if dupes.any():
        print(f"  Dropped {dupes.sum()} duplicate {what} rows")
    return df[~dupes]
