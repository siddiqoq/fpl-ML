import os.path

import joblib
import pandas as pd
from path import MODELS_DIR, PROCESSED_DATA_DIR
from features import FEATURES, next_gw_features

MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")

model = joblib.load(MODEL_PATH)
df = pd.read_csv(DATASET_PATH)

latest_player_gw = next_gw_features(df)
predictedGW = latest_player_gw["gameweek"].max() + 1
latest_player_gw[f"predicted_points_gw{predictedGW}"] = model.predict(latest_player_gw[FEATURES])

predicted_values = (latest_player_gw[["player_id","web_name","short_name","now_cost",f"predicted_points_gw{predictedGW}"]]
                    .sort_values(f"predicted_points_gw{predictedGW}",ascending=False))

print(predicted_values.head(10).reset_index(drop=True))
