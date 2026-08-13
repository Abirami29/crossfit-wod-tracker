import streamlit as st
from datetime import date

# from logic.muscle_mapping import load_workouts
from logic.muscle_mapping import load_workouts, load_movements, compute_muscle_load, format_top_muscles
st.set_page_config(page_title="Log session", page_icon="✅", layout="centered")


@st.cache_data
def get_data():
    return load_workouts(), load_movements()

workouts, (movement_map, muscle_groups) = get_data()
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

with st.form("log_session_form", clear_on_submit=True):
    session_date = st.date_input("Date", value=DEMO_TODAY, max_value=DEMO_TODAY,
                                   help="Capped at the demo's 'today' so it shows up in the Dashboard's rolling windows.")
    submitted = st.form_submit_button("Log session")

    if submitted:
        st.session_state.logged_sessions.append({
            "date": session_date.isoformat(),
            "workout_id": selected["id"],
            "workout_name": workout_name,
        })
        st.success(f"Logged {workout_name} on {session_date.isoformat()} — go to Dashboard to see it reflected in your muscle volume.")

if st.session_state.logged_sessions:
    st.subheader("Logged this session")
    for i in reversed(range(len(st.session_state.logged_sessions))):
        s = st.session_state.logged_sessions[i]
        col_text, col_del = st.columns([5, 1])
        col_text.write(f"- {s['date']} — {s['workout_name']}")
        if col_del.button("Delete", key=f"delete_{i}"):
            st.session_state.logged_sessions.pop(i)
            st.rerun()
    if st.button("Clear all"):
        st.session_state.logged_sessions = []
        st.rerun()
else:
    st.info("Nothing logged yet this session.")