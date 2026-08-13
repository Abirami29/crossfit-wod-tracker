import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_movements():
    with open(DATA_DIR / "movements.json") as f:
        data = json.load(f)
    muscle_groups = data.pop("_muscle_groups")
    return data, muscle_groups


def load_workouts():
    with open(DATA_DIR / "workouts.json") as f:
        return json.load(f)


def compute_muscle_load(workout, movement_map, muscle_groups):
    """
    Sums muscle-weight contributions across every movement in a workout.
    Binary presence model (MVP): each movement contributes its full weight
    regardless of rep count. Returns a dict {muscle_group: score}.
    """
    load = {m: 0.0 for m in muscle_groups}
    unmatched = []

    for entry in workout["movements"]:
        name = entry["movement"]
        weights = movement_map.get(name)
        if weights is None:
            unmatched.append(name)
            continue
        for muscle, weight in weights.items():
            load[muscle] += weight

    return load, unmatched


def normalize_load(load, scale_to=100):
    """Scale the highest muscle group to `scale_to`, others proportionally."""
    peak = max(load.values()) if load else 0
    if peak == 0:
        return {k: 0 for k in load}
    return {k: round((v / peak) * scale_to, 1) for k, v in load.items()}


def top_muscles(load, tolerance=1e-6):
    """
    Returns ALL muscle groups tied at the max load, not just one.
    A workout can genuinely load two groups equally (e.g. Grace: legs & shoulders) -
    silently picking one would misrepresent the workout.
    """
    peak = max(load.values()) if load else 0
    if peak == 0:
        return []
    return [m for m, v in load.items() if abs(v - peak) < tolerance]


def format_top_muscles(load):
    tops = top_muscles(load)
    if not tops:
        return "-"
    return " & ".join(tops)


if __name__ == "__main__":
    movement_map, muscle_groups = load_movements()
    workouts = load_workouts()

    print(f"Loaded {len(movement_map)} movements, {len(muscle_groups)} muscle groups: {muscle_groups}")
    print(f"Loaded {len(workouts)} workouts\n")

    all_unmatched = set()
    for w in workouts:
        load, unmatched = compute_muscle_load(w, movement_map, muscle_groups)
        norm = normalize_load(load)
        top = format_top_muscles(load)
        print(f"{w['name']:10s} [{w['category']:8s}] -> top muscle(s): {top:20s} | raw: {load}")
        if unmatched:
            print(f"   ⚠ unmatched movements: {unmatched}")
            all_unmatched.update(unmatched)

    print("\n--- sanity checks ---")
    if all_unmatched:
        print(f"FAIL: {len(all_unmatched)} movement(s) in workouts.json missing from movements.json: {all_unmatched}")
    else:
        print("PASS: every movement used in workouts.json resolves in movements.json")
