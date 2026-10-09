import os.path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from path import PROCESSED_DATA_DIR, MODELS_DIR
from features import FEATURES
import joblib

INPUT_PATH = os.path.join(PROCESSED_DATA_DIR, 'ml_features_dataset.csv')
MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
df = pd.read_csv(INPUT_PATH)

# only use the current season so gameweek numbers are comparable
df = df[df["season"] == df["season"].max()]

X = df[FEATURES]
y = df["total_points"]

lastGW = df["gameweek"].max()
# hold out the last 2 GWs, or just 1 early in the season when only a few GWs have features
n_gws = df["gameweek"].nunique()
if n_gws < 2:
    raise SystemExit(f"Need at least 2 gameweeks with features to train, have {n_gws}")
cutoff = lastGW - min(2, n_gws - 1)

train_idx = df["gameweek"] <= cutoff
X_train, X_test = X[train_idx], X[~train_idx]
y_train, y_test = y[train_idx], y[~train_idx]

model = RandomForestRegressor(n_estimators=100, min_samples_leaf=20, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
baseline_mae = mean_absolute_error(y_test, X_test["points_last_3_gws"])
print("MAE on test set:", mae)
print("Baseline MAE (avg of last 3 GWs):", baseline_mae)

# refit on every gameweek so the saved model has seen the most recent form
model.fit(X, y)
joblib.dump(model, MODEL_PATH)
print("Model saved")
