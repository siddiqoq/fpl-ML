import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import joblib

df = pd.read_csv("data/processed/ml_features_dataset.csv")

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

joblib.dump(model, "models/rf_model.pkl")
print("Model saved")