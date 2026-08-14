import streamlit as st
from datetime import date

from logic.muscle_mapping import load_workouts, load_movements, compute_muscle_load, format_top_muscles
from logic.scoring import workout_status, format_score
from logic.aggregate import load_sessions

st.set_page_config(page_title="Log session", page_icon="✅", layout="centered")

@st.cache_data
def get_data():
    return load_workouts(), load_movements(), load_sessions()

workouts, (movement_map, muscle_groups), sessions = get_data()
workouts_by_name = {w["name"]: w for w in workouts}

st.title("Log a session")
st.caption(
    "Demo mode: entries below are kept in memory for this browser session only — not saved to a file or "
    "database. They **will** show up in the Dashboard's charts while this session is active, but refreshing "
    "the page (or opening the app in a new tab) clears them. A real deployment would persist this to a database (planned as V2)."
)

if "logged_sessions" not in st.session_state:
    st.session_state.logged_sessions = []

DEMO_TODAY = date(2026, 8, 13)  # matches the sample log's anchor date and the Dashboard's AS_OF

# Selector lives outside the form so details below update immediately on change -
# widgets inside st.form only trigger a rerun on submit, so this couldn't live there.
workout_name = st.selectbox("Workout", sorted(workouts_by_name.keys()))
selected = workouts_by_name[workout_name]

with st.container(border=True):
    load, _ = compute_muscle_load(selected, movement_map, muscle_groups)
    c1, c2 = st.columns(2)
    c1.metric("Format", selected["format"].replace("_", " ").title())
    c2.metric("Top muscle(s)", format_top_muscles(load))
    if selected.get("rounds"):
        st.caption(f"Structure: {selected['rounds']}")
    for m in selected["movements"]:
        reps = f"{m['reps']} " if m.get("reps") is not None else ""
        st.write(f"- {reps}{m.get('unit', '')} — **{m['movement']}**".replace("  ", " "))

    all_sessions = sessions + st.session_state.logged_sessions
    status = workout_status(selected, all_sessions)
    st.divider()
    if status["rx"]["has_pb"]:
        st.success(f"🏆 Your Rx PB: **{status['rx']['pb_display']}** (from {status['rx']['attempt_count']} attempt{'s' if status['rx']['attempt_count'] != 1 else ''})")
    if status["scaled"]["has_pb"]:
        note = " (not directly comparable to Rx benchmark bands)" if status["has_benchmark"] else ""
        st.info(f"Your Scaled PB: **{status['scaled']['pb_display']}** (from {status['scaled']['attempt_count']} attempt{'s' if status['scaled']['attempt_count'] != 1 else ''}){note}")
    if not status["has_any_pb"]:
        if status["has_benchmark"]:
            st.info("You haven't logged this one yet. Your first Rx attempt will be evaluated against the public benchmark ranges below — every attempt after that compares against your own Rx PB instead. Scaled attempts are tracked separately.")
            bands = status["bands"]
            band_order = ["elite", "advanced", "intermediate", "beginner"] if selected["lower_is_better"] else ["beginner", "intermediate", "advanced", "elite"]
            cols = st.columns(4)
            for col, level in zip(cols, band_order):
                lo, hi = bands[level]
                col.metric(level.capitalize(), f"{format_score(lo, status['score_type'])}–{format_score(hi, status['score_type'])}")
        else:
            st.info("You haven't logged this one yet, and there's no public benchmark data for this workout (Open workouts are leaderboard-scored, not band-scored). Your first logged attempt becomes your baseline.")

score_type = selected["score_type"]
score_label = "Time (minutes, e.g. 6.5 for 6:30)" if score_type == "time_minutes" else "Rounds completed (e.g. 15.5 for 15 rounds + partial)"

with st.form("log_session_form", clear_on_submit=True):
    session_date = st.date_input("Date", value=DEMO_TODAY, max_value=DEMO_TODAY,
                                   help="Capped at the demo's 'today' so it shows up in the Dashboard's rolling windows.")
    scale = st.radio(
        "Scale", ["Rx", "Scaled"], horizontal=True,
        help="Rx = as prescribed (full weight/movement). Scaled = reduced weight or an easier movement variant. "
             "Kept as separate PBs since they represent different amounts of work."
    )
    score = st.number_input(score_label, min_value=0.0, step=0.1, format="%.1f")
    submitted = st.form_submit_button("Log session")

    if submitted:
        st.session_state.logged_sessions.append({
            "date": session_date.isoformat(),
            "workout_id": selected["id"],
            "workout_name": workout_name,
            "score": score if score > 0 else None,
            "scale": scale.lower(),
        })
        st.success(f"Logged {workout_name} ({scale}) on {session_date.isoformat()} — go to Dashboard to see it reflected in your muscle volume.")

if st.session_state.logged_sessions:
    st.subheader("Logged this session")
    for i in reversed(range(len(st.session_state.logged_sessions))):
        s = st.session_state.logged_sessions[i]
        wk = workouts_by_name[s["workout_name"]]
        score_str = format_score(s.get("score"), wk["score_type"]) if s.get("score") is not None else "no score recorded"
        scale_str = s.get("scale", "rx").capitalize()
        col_text, col_del = st.columns([5, 1])
        col_text.write(f"- {s['date']} — {s['workout_name']} ({scale_str}, {score_str})")
        if col_del.button("Delete", key=f"delete_{i}"):
            st.session_state.logged_sessions.pop(i)
            st.rerun()
    if st.button("Clear all"):
        st.session_state.logged_sessions = []
        st.rerun()
else:
    st.info("Nothing logged yet this session.")
