import os.path

import joblib
import pandas as pd
from path import MODELS_DIR, PROCESSED_DATA_DIR

MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
FEATURE_DS = os.path.join(PROCESSED_DATA_DIR, "ml_features_dataset.csv")

model = joblib.load(MODEL_PATH)
df = pd.read_csv(FEATURE_DS)

lastGW = df["gameweek"].max()
predictedGW = lastGW + 1

latest_player_gw = df.groupby("player_id").tail(1).reset_index(drop=True)
X_next = latest_player_gw[["points_last_gw","points_last_3_gws"]]
latest_player_gw[f"predicted_points_gw{predictedGW}"] = model.predict(X_next)

predicted_values = (latest_player_gw[["player_id","web_name","short_name","now_cost",f"predicted_points_gw{predictedGW}"]]
                    .sort_values(f"predicted_points_gw{predictedGW}",ascending=False))

print(predicted_values.head(10).reset_index(drop=True))
