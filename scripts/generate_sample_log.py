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

# Weighting: higher weight = logged more often.
# Back-dominant workouts (fran, diane, dt) intentionally underweighted
# to create a visible "neglected: back" signal in the last 30 days.
weights = {
    "fran": 1,
    "grace": 3,
    "cindy": 4,
    "diane": 1,
    "murph": 2,
    "dt": 1,
    "kalsu": 2,
    "25.1": 3,
    "25.2": 2,
    "25.3": 2,
    "26.1": 4,
    "26.2": 3,
    "26.3": 2,
}

ids = list(weights.keys())
w = [weights[i] for i in ids]

today = date(2026, 8, 13)
start = today - timedelta(days=90)

sessions = []
d = start
# roughly 3-4 sessions/week: skip most days, hit workout days
day = 0
while d <= today:
    day += 1
    # ~0.45 chance any given day is a training day -> ~3.15/week
    if random.random() < 0.45:
        workout_id = random.choices(ids, weights=w, k=1)[0]
        sessions.append({"date": d.isoformat(), "workout_id": workout_id, "workout_name": by_id[workout_id]["name"]})
    d += timedelta(days=1)

with open("data/session_log.json", "w") as f:
    json.dump(sessions, f, indent=2)

print(f"Generated {len(sessions)} sessions from {start} to {today}")
