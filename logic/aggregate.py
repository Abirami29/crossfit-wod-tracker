import json
from datetime import date, timedelta
from pathlib import Path
try:
    from logic.muscle_mapping import load_movements, load_workouts, compute_muscle_load
except ImportError:
    from muscle_mapping import load_movements, load_workouts, compute_muscle_load

DATA_DIR = Path(__file__).parent.parent / "data"


def load_sessions():
    with open(DATA_DIR / "session_log.json") as f:
        return json.load(f)


def aggregate_volume(sessions, workouts_by_id, movement_map, muscle_groups, window_days, as_of=None):
    """
    Sums muscle load across every session in the last `window_days`.
    Returns {muscle_group: total_score}.
    """
    as_of = as_of or date.today()
    cutoff = as_of - timedelta(days=window_days)

    volume = {m: 0.0 for m in muscle_groups}
    counted = 0
    for s in sessions:
        session_date = date.fromisoformat(s["date"])
        if not (cutoff < session_date <= as_of):
            continue
        workout = workouts_by_id.get(s["workout_id"])
        if workout is None:
            continue
        load, _ = compute_muscle_load(workout, movement_map, muscle_groups)
        for muscle, v in load.items():
            volume[muscle] += v
        counted += 1

    return volume, counted


def classify_tiers(volume, top_ratio=1.3, neglect_ratio=0.4):
    """
    Buckets each muscle group into 'top' / 'moderate' / 'neglected' relative
    to the average across all groups. Same underlying threshold as
    flag_neglected (kept in sync deliberately - see that function) but adds
    a 'top' tier so muscle groups that are trained but not the single
    highest aren't visually lumped in with genuinely neglected ones.
    """
    values = list(volume.values())
    if not values or sum(values) == 0:
        return {m: "moderate" for m in volume}
    avg = sum(values) / len(values)
    tiers = {}
    for m, v in volume.items():
        if v < avg * neglect_ratio:
            tiers[m] = "neglected"
        elif v >= avg * top_ratio:
            tiers[m] = "top"
        else:
            tiers[m] = "moderate"
    return tiers


def flag_neglected(volume, threshold_ratio=0.4):
    """
    Flags muscle groups whose volume is below `threshold_ratio` of the
    average volume across all groups. Simple, explainable rule for MVP -
    not a statistically rigorous method, just enough to surface a signal.
    Implemented on top of classify_tiers so there's one threshold, not two
    copies that could drift out of sync.
    """
    tiers = classify_tiers(volume, neglect_ratio=threshold_ratio)
    return [m for m, t in tiers.items() if t == "neglected"]


if __name__ == "__main__":
    movement_map, muscle_groups = load_movements()
    workouts = load_workouts()
    workouts_by_id = {w["id"]: w for w in workouts}
    sessions = load_sessions()

    as_of = date(2026, 8, 13)  # matches the generated log's "today"

    for window in (7, 30, 90):
        volume, count = aggregate_volume(sessions, workouts_by_id, movement_map, muscle_groups, window, as_of)
        neglected = flag_neglected(volume)
        print(f"\n--- last {window} days ({count} sessions) ---")
        for m in muscle_groups:
            marker = " <- NEGLECTED" if m in neglected else ""
            print(f"  {m:10s}: {volume[m]:.2f}{marker}")
