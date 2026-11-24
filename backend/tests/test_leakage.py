import pandas as pd

from features import FEATURES, LAST_3_STATS, LAST_GW_STATS, SEASON_STATS, add_training_features, next_gw_features
from replay import PREDICT_COLUMNS, LastGW, Model, Rolling3, StaticRF, replay_season
from seasons import EVENTS, TEST, TUNING, XG_TEST, XG_TUNING, role


def change_points_from(raw, season, gw):
    # the same data with every stat from (season, gw) onwards changed
    changed = raw.copy()
    future = (changed["season"] == season) & (changed["gameweek"] >= gw)
    stats = list(dict.fromkeys(LAST_GW_STATS + LAST_3_STATS + SEASON_STATS))
    changed.loc[future, stats] += 50
    return changed


def test_features_only_use_earlier_gameweeks(raw):
    before = add_training_features(raw)
    after = add_training_features(change_points_from(raw, "2022/23", 6))
    key = ["season", "player_id", "gameweek"]
    merged = before.merge(after, on=key, suffixes=("", "_changed"))
    up_to_gw6 = ~((merged["season"] == "2022/23") & (merged["gameweek"] > 6))
    for f in FEATURES:
        assert (merged.loc[up_to_gw6, f] == merged.loc[up_to_gw6, f"{f}_changed"]).all()


def test_features_restart_each_season(raw):
    df = add_training_features(raw)
    # points_last_3_gws needs 3 earlier GWs of the same season, so GW4 is the first row of each season
    assert df.groupby("season")["gameweek"].min().eq(4).all()


def test_replay_predictions_dont_change_when_the_future_does(raw):
    season, gw = "2022/23", 6
    models = lambda: [LastGW(), Rolling3(), StaticRF()]
    before = replay_season(add_training_features(raw), season, models())
    after = replay_season(add_training_features(change_points_from(raw, season, gw)), season, models())
    cols = ["last_gw", "rolling_3", "static_rf"]
    pd.testing.assert_frame_equal(before.loc[before["gameweek"] <= gw, cols],
                                  after.loc[after["gameweek"] <= gw, cols])


class Recorder(Model):
    name = "recorder"

    def start(self, history):
        self.history_seasons = set(history["season"])
        self.seen = []

    def predict(self, rows):
        self.seen.append((set(rows.columns), rows["gameweek"].iloc[0]))
        return rows["points_last_gw"].to_numpy()

    def observe(self, rows):
        self.revealed = rows["gameweek"].iloc[0]


def test_models_get_no_outcomes_and_only_earlier_seasons(raw):
    model = Recorder()
    replay_season(add_training_features(raw), "2022/23", [model])
    assert model.history_seasons == {"2021/22"}
    for columns, _ in model.seen:
        assert columns == set(PREDICT_COLUMNS)
        assert not {"total_points", "minutes"} & columns


def test_season_roles_dont_overlap():
    main = [set(TUNING), set(EVENTS), set(TEST)]
    assert sum(len(s) for s in main) == len(set().union(*main))
    assert not set(XG_TUNING) & set(XG_TEST)
    for year in range(2016, 2027):
        role(f"{year}/{(year + 1) % 100:02d}")  # every season in the DB has a role


def test_features_match_a_plain_per_player_loop(raw):
    # the vectorised builder against the obvious slow version, for training and next-GW features
    df = add_training_features(raw).set_index(["season", "player_id", "gameweek"])
    latest = next_gw_features(raw).set_index("player_id")
    for (season, player_id), g in raw.sort_values("gameweek").groupby(["season", "player_id"]):
        for i in range(3, len(g)):
            row, past = g.iloc[i], g.iloc[:i]
            got = df.loc[(season, player_id, row["gameweek"])]
            assert got["points_last_gw"] == past["total_points"].iloc[-1]
            assert got["minutes_last_3_gws"] == past["minutes"].iloc[-3:].mean()
            assert got["bps_last_3_gws"] == past["bps"].iloc[-3:].mean()
            assert abs(got["points_per_gw_season"] - past["total_points"].mean()) < 1e-9
        if season == "2022/23":  # latest season: next-GW features include the last GW
            assert latest.loc[player_id, "points_last_gw"] == g["total_points"].iloc[-1]
            assert latest.loc[player_id, "threat_last_3_gws"] == g["threat"].iloc[-3:].mean()
