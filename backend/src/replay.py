import argparse
import os.path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from features import FEATURES, add_training_features
from path import PROCESSED_DATA_DIR
from seasons import role

# Walk-forward replay. Each season is stepped through GW by GW:
# every model predicts GW t using only data from before GW t, then GW t's results are revealed to it.
# Writes per-player predictions and a per-GW error table (the error stream the detectors will read).
#   python src/replay.py                  -> every season
#   python src/replay.py 2021/22 2022/23  -> just those (earlier seasons are still used as history)

ID_COLUMNS = ["season", "player_id", "code", "gameweek", "element_type"]
# All a model sees when predicting GW t: who the row is, features built from earlier GWs, and FPL's
# own pre-deadline xP. GW t's outcomes (points, minutes, goals, ...) are never passed in.
PREDICT_COLUMNS = ID_COLUMNS + FEATURES + ["xp"]

DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")
PREDICTIONS_PATH = os.path.join(PROCESSED_DATA_DIR, "replay_predictions.csv")
ERRORS_PATH = os.path.join(PROCESSED_DATA_DIR, "replay_gw_errors.csv")


class Model:
    # start(history): every row from earlier seasons, before the season begins
    # predict(rows): GW t's rows, PREDICT_COLUMNS only
    # observe(rows): GW t's full rows once revealed; retraining strategies (3.1) will use this
    name = "model"

    def start(self, history):
        pass

    def predict(self, rows):
        raise NotImplementedError

    def observe(self, rows):
        pass


class LastGW(Model):
    name = "last_gw"

    def predict(self, rows):
        return rows["points_last_gw"].to_numpy()


class Rolling3(Model):
    # baseline from objective 1.3: the player's average over their previous 3 GWs
    name = "rolling_3"

    def predict(self, rows):
        return rows["points_last_3_gws"].to_numpy()


class FplXP(Model):
    # FPL's own expected points; NaN where vaastav didn't record it (none before 2020/21)
    name = "fpl_xp"

    def predict(self, rows):
        return rows["xp"].to_numpy(dtype=float)


class StaticRF(Model):
    # trained once on all earlier seasons when the season starts, never retrained during it:
    # the "never retrained" reference that retraining strategies are compared against
    name = "static_rf"

    def start(self, history):
        self.model = None
        if not history.empty:
            self.model = RandomForestRegressor(n_estimators=100, min_samples_leaf=20, n_jobs=-1, random_state=42)
            self.model.fit(history[FEATURES], history["total_points"])

    def predict(self, rows):
        if self.model is None:  # first season: nothing to train on
            return np.full(len(rows), np.nan)
        return self.model.predict(rows[FEATURES])


def replay_season(df, season, models):
    history = df[df["season"] < season]
    current = df[df["season"] == season]
    for model in models:
        model.start(history)

    out = []
    for gw in sorted(current["gameweek"].unique()):
        rows = current[current["gameweek"] == gw]
        preds = rows[ID_COLUMNS + ["minutes", "total_points"]].copy()
        for model in models:
            preds[model.name] = model.predict(rows[PREDICT_COLUMNS].copy())
        for model in models:
            model.observe(rows)
        out.append(preds)
    return pd.concat(out, ignore_index=True)


def gw_errors(preds, model_names):
    # one row per season, GW and model; each model is scored on the rows it made a prediction for (n)
    long = preds.melt(id_vars=ID_COLUMNS + ["minutes", "total_points"], value_vars=model_names,
                      var_name="model", value_name="pred").dropna(subset=["pred"])
    long["resid"] = long["total_points"] - long["pred"]
    long["abs_resid"] = long["resid"].abs()
    long["sq_resid"] = long["resid"] ** 2
    long["abs_resid_played"] = long["abs_resid"].where(long["minutes"] > 0)
    errors = long.groupby(["season", "gameweek", "model"]).agg(
        n=("resid", "size"), mae=("abs_resid", "mean"), bias=("resid", "mean"),
        rmse=("sq_resid", "mean"), mae_played=("abs_resid_played", "mean")).reset_index()
    errors["rmse"] = np.sqrt(errors["rmse"])
    errors.insert(1, "role", errors["season"].map(role))
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("seasons", nargs="*", help="e.g. 2021/22 (default: every season)")
    args = parser.parse_args()

    df = add_training_features(pd.read_csv(DATASET_PATH, low_memory=False))
    seasons = args.seasons or sorted(df["season"].unique())
    models = [LastGW(), Rolling3(), FplXP(), StaticRF()]
    names = [m.name for m in models]

    preds = []
    for season in seasons:
        print(f"Replaying {season} ({role(season)})")
        preds.append(replay_season(df, season, models))
    preds = pd.concat(preds, ignore_index=True)
    errors = gw_errors(preds, names)

    preds.to_csv(PREDICTIONS_PATH, index=False)
    errors.to_csv(ERRORS_PATH, index=False)
    print(f"Saved {PREDICTIONS_PATH} and {ERRORS_PATH}")

    # MAE over the season's rows (fpl_xp only covers rows where xP was recorded: see n)
    long = preds.melt(id_vars=["season", "total_points"], value_vars=names, var_name="model", value_name="pred")
    long = long.dropna(subset=["pred"]).assign(abs_resid=lambda d: (d["total_points"] - d["pred"]).abs())
    summary = long.groupby(["season", "model"])["abs_resid"].agg(["mean", "size"]).unstack("model")
    print("\nMAE per season")
    print(summary["mean"][names].round(3).to_string())
    print("\nRows scored")
    print(summary["size"][names].fillna(0).astype(int).to_string())
