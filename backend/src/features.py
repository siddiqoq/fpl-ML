import pandas as pd

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
