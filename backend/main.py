import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os.path
import joblib
import pandas as pd
from src.path import MODELS_DIR, PROCESSED_DATA_DIR
from src.features import FEATURES, next_gw_features


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

MODEL_PATH = os.path.join(MODELS_DIR, 'rf_model.pkl')
DATASET_PATH = os.path.join(PROCESSED_DATA_DIR, "ml_dataset.csv")

model = joblib.load(MODEL_PATH)
df = pd.read_csv(DATASET_PATH)

latest_player_gw = next_gw_features(df)
latest_player_gw["predicted_points"] = model.predict(latest_player_gw[FEATURES])

@app.get("/")
def top_10(position: int = Query(0, ge=0, le=4)):
    players = latest_player_gw
    if position != 0: # 0 = all positions
        players = players[players["element_type"] == position]

    predicted_values = (players[["player_id","web_name","short_name","now_cost","predicted_points","points_last_gw","ict_index","element_type"]]
                        .sort_values("predicted_points",ascending=False)).reset_index(drop=True)

    return predicted_values.head(10).to_dict(orient='records')

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
