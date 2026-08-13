"""
Handles the 'how good was this score' question, separate from muscle-load
math. Two paths:
  1. Athlete has a prior logged score for this workout -> compare against
     their own personal best (self-referential, no external data needed).
  2. No prior score -> classify against public benchmark bands, if they
     exist for this workout (only the 7 Girls/Heroes have real sourced
     bands - see data/BENCHMARKS.md). Open workouts have no bands, so
     first attempt just gets logged with no classification.
"""


def get_personal_best(workout_id, sessions):
    """
    Returns the best (lowest time / highest rounds) score logged for this
    workout, or None if there's no prior scored session for it.
    """
    scored = [s for s in sessions if s["workout_id"] == workout_id and s.get("score") is not None]
    if not scored:
        return None
    return scored  # caller reduces by direction; kept as list so ties/history are inspectable


def best_score(workout, sessions):
    scored = [s["score"] for s in sessions if s["workout_id"] == workout["id"] and s.get("score") is not None]
    if not scored:
        return None
    return min(scored) if workout["lower_is_better"] else max(scored)


def classify_level(workout, score):
    """
    Returns 'beginner' / 'intermediate' / 'advanced' / 'elite', or None if
    this workout has no public benchmark bands (e.g. Open workouts) or the
    score doesn't fall cleanly in any band.
    """
    bands = workout.get("benchmark_bands")
    if not bands or score is None:
        return None

    order = ["elite", "advanced", "intermediate", "beginner"] if workout["lower_is_better"] else ["beginner", "intermediate", "advanced", "elite"]
    for level in order:
        lo, hi = bands[level]
        if lo <= score <= hi:
            return level

    # outside all bands (e.g. much slower than "beginner" range) - closest edge case
    if workout["lower_is_better"]:
        return "beginner" if score > bands["beginner"][1] else "elite"
    else:
        return "beginner" if score < bands["beginner"][0] else "elite"


def format_score(score, score_type):
    if score is None:
        return "-"
    if score_type == "time_minutes":
        minutes = int(score)
        seconds = round((score - minutes) * 60)
        return f"{minutes}:{seconds:02d}"
    return f"{score:g} rounds"


def workout_status(workout, sessions):
    """
    Single entry point the UI calls: returns a dict describing what to show
    for a given workout - either a PB (with history count) or a benchmark
    classification prompt, or neither if no data exists at all.
    """
    pb = best_score(workout, sessions)
    attempt_count = len([s for s in sessions if s["workout_id"] == workout["id"] and s.get("score") is not None])

    if pb is not None:
        return {
            "has_pb": True,
            "pb": pb,
            "pb_display": format_score(pb, workout["score_type"]),
            "attempt_count": attempt_count,
        }
    else:
        return {
            "has_pb": False,
            "has_benchmark": workout.get("benchmark_bands") is not None,
            "bands": workout.get("benchmark_bands"),
            "score_type": workout["score_type"],
        }


if __name__ == "__main__":
    import json
    from pathlib import Path
    DATA_DIR = Path(__file__).parent.parent / "data"

    with open(DATA_DIR / "workouts.json") as f:
        workouts = json.load(f)

    # sanity test with fake sessions
    fake_sessions = [
        {"workout_id": "fran", "score": 6.5, "date": "2026-07-01"},
        {"workout_id": "fran", "score": 5.8, "date": "2026-07-15"},
    ]

    fran = next(w for w in workouts if w["id"] == "fran")
    status = workout_status(fran, fake_sessions)
    print("Fran with 2 logged attempts:", status)
    assert status["has_pb"] and status["pb"] == 5.8, "PB should be the faster (lower) of the two times"

    grace = next(w for w in workouts if w["id"] == "grace")
    status = workout_status(grace, [])
    print("Grace with no attempts:", status)
    assert status["has_pb"] is False and status["has_benchmark"] is True

    open_wod = next(w for w in workouts if w["id"] == "26.1")
    status = workout_status(open_wod, [])
    print("Open 26.1 with no attempts:", status)
    assert status["has_benchmark"] is False, "Open workouts should have no public benchmark"

    print("\nAll sanity checks passed")
