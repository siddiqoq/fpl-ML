import os.path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from path import PROCESSED_DATA_DIR, MODELS_DIR
import joblib

INPUT_PATH = os.path.join(PROCESSED_DATA_DIR, 'ml_features_dataset.csv')
MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
df = pd.read_csv(INPUT_PATH)

X = df[["points_last_gw", "points_last_3_gws"]]
y = df["total_points"]

lastGW = df["gameweek"].max()
cutoff = lastGW - 2

train_idx = df["gameweek"] <= cutoff
X_train, X_test = X[train_idx], X[~train_idx]
y_train, y_test = y[train_idx], y[~train_idx]

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
print("MAE on test set:", mae)


joblib.dump(model, MODEL_PATH)
print("Model saved")