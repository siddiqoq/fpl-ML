import os

import pandas as pd
from path import PROCESSED_DATA_DIR
from db.conn import get_engine
from db.ingest import STAT_COLUMNS

engine = get_engine()
stats = pd.read_sql("SELECT * FROM player_fixture_stats", engine)
players = pd.read_sql("SELECT season, player_id, code, first_name, second_name, web_name, element_type FROM players", engine)
teams = pd.read_sql("SELECT season, team_id, name, short_name FROM teams", engine)

# Features and targets are per gameweek: a double gameweek's two fixtures are summed into one row,
# and a blank gameweek has no row. Price/ownership/transfers/xP are per-gameweek values, so take
# the latest fixture's value instead of summing. min_count=1 keeps stats a season never recorded NULL.
PER_GW_COLUMNS = ["value", "selected", "transfers_in", "transfers_out", "transfers_balance", "xp"]
SUMMED_COLUMNS = [c for c in STAT_COLUMNS if c not in PER_GW_COLUMNS]

stats = stats.sort_values(["season", "player_id", "gameweek", "kickoff_time"])
by_gw = stats.groupby(["season", "player_id", "gameweek"])
df = pd.concat([
    by_gw[SUMMED_COLUMNS].sum(min_count=1),
    by_gw[PER_GW_COLUMNS + ["team_id"]].last(),
    by_gw.size().rename("n_fixtures"),
    by_gw["was_home"].sum().rename("home_fixtures"),  # 0-2: a double GW can be home, away or both
], axis=1).reset_index()

df = df.rename(columns={"value": "now_cost"})  # price at that gameweek, x10
df = df.merge(players, on=["season", "player_id"], how="left")
df = df.merge(teams, on=["season", "team_id"], how="left")  # team the player played for that gameweek

DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
df.to_csv(DATASET_PATH, index=False)
print("ML dataset created:", df.shape)
print(df.groupby("season").size().to_string())
