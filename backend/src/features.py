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

# Every feature is built from CORE_STATS of the player's earlier gameweeks in the same season, including
# price/ownership/transfers (whether vaastav records those at the deadline isn't certain, so the previous
# GW's value is used). n_fixtures/home_fixtures describe the upcoming GW itself; they aren't features yet
# because next_gw_features would need next GW's fixtures from the fixtures table.
LAST_GW_STATS = ["total_points", "minutes", "now_cost", "selected", "transfers_balance"]
LAST_3_STATS = ["total_points", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded",
                "saves", "bonus", "bps", "influence", "creativity", "threat"]
SEASON_STATS = ["total_points", "minutes"]  # per-GW average over the season so far


def _name(stat):
    return "points" if stat == "total_points" else stat


# Single source of truth for model inputs, shared by training, prediction and the API
FEATURES = ([f"{_name(s)}_last_gw" for s in LAST_GW_STATS] + [f"{_name(s)}_last_3_gws" for s in LAST_3_STATS]
            + [f"{_name(s)}_per_gw_season" for s in SEASON_STATS])


def _build_features(df, shift):
    # shift=1: a row's features come only from GWs before it (training/replay rows).
    # shift=0: they include the row's own GW (the latest row, used to predict the next GW).
    df = df.sort_values(["season", "player_id", "gameweek"]).copy()
    keys = [df["season"], df["player_id"]]
    stats = list(dict.fromkeys(LAST_GW_STATS + LAST_3_STATS + SEASON_STATS))
    past = df[stats].groupby(keys).shift(shift) if shift else df[stats]
    by_player = past.groupby(keys)

    last_3 = by_player[LAST_3_STATS].rolling(3).mean().reset_index(level=[0, 1], drop=True)
    season = by_player[SEASON_STATS].expanding().mean().reset_index(level=[0, 1], drop=True)
    for s in LAST_GW_STATS:
        df[f"{_name(s)}_last_gw"] = past[s]
    for s in LAST_3_STATS:
        df[f"{_name(s)}_last_3_gws"] = last_3[s]
    for s in SEASON_STATS:
        df[f"{_name(s)}_per_gw_season"] = season[s]
    return df


def add_training_features(df: pd.DataFrame) -> pd.DataFrame:
    # each row only sees gameweeks strictly before it, so the target never leaks into its features;
    # rows without 3 earlier GWs that season are dropped
    return _build_features(df, shift=1).dropna(subset=FEATURES)


def next_gw_features(df: pd.DataFrame) -> pd.DataFrame:
    # one row per player in the latest season, with features that include their most recent gameweek,
    # i.e. what the model needs to predict the *upcoming* gameweek
    latest = _build_features(df[df["season"] == df["season"].max()], shift=0)
    return latest.groupby("player_id").tail(1).dropna(subset=FEATURES).reset_index(drop=True)
