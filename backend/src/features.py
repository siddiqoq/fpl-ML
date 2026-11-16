import pandas as pd

# Raw stats recorded in every season from 2016/17. The main experiments build features only from
# these, so tuning seasons (pre-2022) and test seasons see the same inputs. Fixture difficulty is not
# here: 2016/17 and 2017/18 have no fixtures.csv, so their difficulty is NULL.
CORE_STATS = [
    "total_points", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals",
    "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "bps",
    "influence", "creativity", "threat", "ict_index", "now_cost", "selected", "transfers_in",
    "transfers_out", "transfers_balance", "n_fixtures", "home_fixtures",
]
# Only recorded from 2022/23 (xG family, starts). Used only in a separate xG ablation on 2022/23
# onwards, never in the main experiments: as NaN in older seasons the model would learn the era from
# the missingness. Defensive stats (2025/26 on) are for the rule-change experiment, not features.
XG_ERA_STATS = ["starts", "expected_goals", "expected_assists", "expected_goal_involvements",
                "expected_goals_conceded"]

# Single source of truth for model inputs, shared by training, prediction and the API
FEATURES = ["points_last_gw", "points_last_3_gws"]


def add_training_features(df: pd.DataFrame) -> pd.DataFrame:
    # each row only sees gameweeks strictly before it, so the target never leaks into its features
    df = df.sort_values(["season", "player_id", "gameweek"]).copy()
    points = df.groupby(["season", "player_id"])["total_points"]
    df["points_last_gw"] = points.shift(1)
    df["points_last_3_gws"] = points.transform(lambda s: s.rolling(3).mean().shift(1))
    return df.dropna(subset=FEATURES)


def next_gw_features(df: pd.DataFrame) -> pd.DataFrame:
    # one row per player in the latest season, with features that include their most recent gameweek,
    # i.e. what the model needs to predict the *upcoming* gameweek
    latest = df[df["season"] == df["season"].max()].sort_values(["player_id", "gameweek"]).copy()
    points = latest.groupby("player_id")["total_points"]
    latest["points_last_gw"] = latest["total_points"]
    latest["points_last_3_gws"] = points.transform(lambda s: s.rolling(3).mean())
    return latest.groupby("player_id").tail(1).dropna(subset=FEATURES).reset_index(drop=True)
