"""
Generates a synthetic 90-day workout log for demo purposes.
Deliberately biased toward leg/shoulder-dominant workouts in recent weeks,
with back-dominant workouts (Fran, Diane, DT) appearing rarely - so the
aggregate dashboard has a real, visible imbalance to flag. This is fake
data standing in for what a real logged history would look like.
"""
import json
import random
from datetime import date, timedelta

random.seed(42)

with open("data/workouts.json") as f:
    workouts = json.load(f)

by_id = {w["id"]: w for w in workouts}


def synthetic_scale(days_ago, total_days=90):
    """
    Simulates an athlete gradually moving from scaled toward Rx over the
    90-day window: early sessions more likely scaled, recent sessions more
    likely Rx. Open workouts (no benchmark bands) are always logged as Rx
    since there's no meaningful "scaled" reference for those in this demo.
    """
    progress = 1 - (days_ago / total_days)  # 0 = 90 days ago, 1 = today
    rx_probability = 0.25 + progress * 0.65  # starts ~25% Rx, ends ~90% Rx
    return "rx" if random.random() < rx_probability else "scaled"


def synthetic_score(workout, days_ago, scale, total_days=90):
    """
    Generates a plausible score for this workout. For workouts with public
    benchmark bands, centers on 'intermediate' with random variation and a
    slight improvement trend as days_ago decreases (more recent = better,
    simulating a fitness gain over the 90-day window). Scaled attempts get
    a ~20% discount applied (faster time / more rounds) since less weight
    or an easier movement variant means less total work, not more fitness -
    a scaled PB should not read as "better" than it actually represents.
    For Open workouts (no bands), just picks a plausible-looking number in
    a generic range - there's no real reference to anchor to, so this is
    illustrative only.
    """
    progress = 1 - (days_ago / total_days)  # 0 = 90 days ago, 1 = today
    improvement = progress * 0.12  # up to ~12% better by the end of the window
    scale_discount = 0.20 if scale == "scaled" else 0.0

    bands = workout.get("benchmark_bands")
    if bands:
        lo, hi = bands["intermediate"]
        base = random.uniform(lo, hi)
        if workout["lower_is_better"]:
            return round(base * (1 - improvement) * (1 - scale_discount), 1)
        else:
            return round(base * (1 + improvement) * (1 + scale_discount), 1)

    # Open workouts: no real reference data - illustrative only
    if workout["score_type"] == "time_minutes":
        return round(random.uniform(8, 18) * (1 - improvement), 1)
    else:
        return round(random.uniform(80, 200) * (1 + improvement))


# Weighting: higher weight = logged more often.
# Back-dominant workouts (fran, diane, dt) intentionally underweighted
# to create a visible "neglected: back" signal in the last 30 days.
weights = {
    "fran": 1, "grace": 3, "cindy": 4, "diane": 1, "murph": 2, "dt": 1, "kalsu": 2,
    "25.1": 3, "25.2": 2, "25.3": 2, "26.1": 4, "26.2": 3, "26.3": 2,
}

ids = list(weights.keys())
w = [weights[i] for i in ids]

today = date(2026, 8, 13)
start = today - timedelta(days=90)

sessions = []
d = start
while d <= today:
    if random.random() < 0.45:
        workout_id = random.choices(ids, weights=w, k=1)[0]
        workout = by_id[workout_id]
        days_ago = (today - d).days
        scale = "rx" if not workout.get("benchmark_bands") else synthetic_scale(days_ago)
        score = synthetic_score(workout, days_ago, scale)
        sessions.append({
            "date": d.isoformat(),
            "workout_id": workout_id,
            "workout_name": workout["name"],
            "score": score,
            "scale": scale,
        })
    d += timedelta(days=1)

with open("data/session_log.json", "w") as f:
    json.dump(sessions, f, indent=2)

print(f"Generated {len(sessions)} sessions from {start} to {today}, each with a synthetic score")
