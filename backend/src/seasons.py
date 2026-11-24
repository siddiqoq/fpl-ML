# Season roles for every experiment, fixed on 17 Nov 2026 before any replay results were seen.
# Detector thresholds and strategy/model hyperparameters (h, k, window N, decay rate, ...) are chosen
# on TUNING seasons only. TEST seasons are only ever evaluated, never tuned on.

# normal seasons; 2023/24 gives tuning one season from the 5-sub, xG era
TUNING = ["2016/17", "2017/18", "2018/19", "2021/22", "2023/24"]

# real drift with a known cause, kept out of tuning and used as labelled events (objective 2.3)
EVENTS = {
    "2019/20": "COVID suspension; restart from GW39 (FPL renumbering) behind closed doors with 5 subs",
    "2020/21": "played almost entirely without crowds (weaker home advantage)",
}

# 2022/23: 5 subs made permanent + World Cup break; 2024/25: normal season (false-alarm check);
# 2025/26: defensive contribution points added; 2026/27: live season
TEST = ["2022/23", "2024/25", "2025/26", "2026/27"]

# xG/xA only exist from 2022/23, so the core vs core+xG ablation has its own split
XG_TUNING = ["2022/23", "2023/24"]
XG_TEST = ["2024/25", "2025/26"]


def role(season):
    if season in TUNING:
        return "tuning"
    if season in EVENTS:
        return "event"
    if season in TEST:
        return "test"
    raise ValueError(f"Season {season} has no role in seasons.py")
