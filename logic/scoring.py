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


def best_score(workout, sessions, scale=None):
    """
    scale: 'rx', 'scaled', or None (any). Rx and Scaled attempts are NOT
    comparable to each other - a fast scaled time can look "better" than a
    slower Rx time while representing less actual work, so they're kept as
    two separate personal bests rather than one merged number.
    """
    scored = [
        s["score"] for s in sessions
        if s["workout_id"] == workout["id"]
        and s.get("score") is not None
        and (scale is None or s.get("scale", "rx") == scale)
    ]
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


def _scale_summary(workout, sessions, scale):
    pb = best_score(workout, sessions, scale=scale)
    count = len([
        s for s in sessions if s["workout_id"] == workout["id"]
        and s.get("score") is not None and s.get("scale", "rx") == scale
    ])
    if pb is None:
        return {"has_pb": False, "attempt_count": 0}
    return {
        "has_pb": True,
        "pb": pb,
        "pb_display": format_score(pb, workout["score_type"]),
        "attempt_count": count,
    }


def workout_status(workout, sessions):
    """
    Single entry point the UI calls. Rx and Scaled are reported separately -
    an athlete progressing from scaled toward Rx should see both, not one
    number that quietly mixes the two. Public benchmark bands (where they
    exist) assume Rx weights/movements, so they're only offered as a
    comparison point when there's no Rx PB yet; a Scaled PB is shown but
    flagged as not directly comparable to those bands.
    """
    rx = _scale_summary(workout, sessions, "rx")
    scaled = _scale_summary(workout, sessions, "scaled")

    return {
        "rx": rx,
        "scaled": scaled,
        "has_any_pb": rx["has_pb"] or scaled["has_pb"],
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

    # sanity test with fake sessions - mix of Rx and Scaled
    fake_sessions = [
        {"workout_id": "fran", "score": 8.0, "date": "2026-06-01", "scale": "scaled"},
        {"workout_id": "fran", "score": 6.5, "date": "2026-07-01", "scale": "rx"},
        {"workout_id": "fran", "score": 5.8, "date": "2026-07-15", "scale": "rx"},
    ]

    fran = next(w for w in workouts if w["id"] == "fran")
    status = workout_status(fran, fake_sessions)
    print("Fran with 1 scaled + 2 Rx attempts:", status)
    assert status["rx"]["has_pb"] and status["rx"]["pb"] == 5.8, "Rx PB should be the faster of the two Rx times"
    assert status["scaled"]["has_pb"] and status["scaled"]["pb"] == 8.0, "Scaled PB tracked separately from Rx"
    assert status["rx"]["attempt_count"] == 2 and status["scaled"]["attempt_count"] == 1

    grace = next(w for w in workouts if w["id"] == "grace")
    status = workout_status(grace, [])
    print("Grace with no attempts:", status)
    assert status["has_any_pb"] is False and status["has_benchmark"] is True

    open_wod = next(w for w in workouts if w["id"] == "26.1")
    status = workout_status(open_wod, [])
    print("Open 26.1 with no attempts:", status)
    assert status["has_benchmark"] is False, "Open workouts should have no public benchmark"

    print("\nAll sanity checks passed")
