import streamlit as st
import plotly.graph_objects as go
from datetime import date

from logic.muscle_mapping import load_movements, load_workouts
from logic.aggregate import load_sessions, aggregate_volume, flag_neglected

st.set_page_config(page_title="Crossfit Muscle Tracker", page_icon="🏋", layout="wide")

# ---- load data (cached so it's not reloaded on every interaction) ----
@st.cache_data
def get_data():
    movement_map, muscle_groups = load_movements()
    workouts = load_workouts()
    workouts_by_id = {w["id"]: w for w in workouts}
    sessions = load_sessions()
    return movement_map, muscle_groups, workouts, workouts_by_id, sessions

movement_map, muscle_groups, workouts, workouts_by_id, sessions = get_data()

# merge in any workouts logged during this browser session (in-memory only)
if "logged_sessions" not in st.session_state:
    st.session_state.logged_sessions = []
all_sessions = sessions + st.session_state.logged_sessions

AS_OF = date(2026, 8, 13)  # anchor date matching the sample log; a live app would use date.today()

st.title("Your training balance")

window = st.radio("Window", [7, 30, 90], index=1, format_func=lambda d: f"{d} days", horizontal=True, label_visibility="collapsed")

volume, session_count = aggregate_volume(all_sessions, workouts_by_id, movement_map, muscle_groups, window, AS_OF)
neglected = flag_neglected(volume)

# ---- metric cards ----
col1, col2, col3, col4 = st.columns(4)
top_muscle = max(volume, key=volume.get) if any(volume.values()) else "-"
col1.metric("Sessions", session_count)
col2.metric("Most trained", top_muscle.capitalize())
col3.metric("Neglected", " & ".join(m.capitalize() for m in neglected) if neglected else "None")
total = sum(volume.values())
balance = round((1 - (max(volume.values()) - min(volume.values())) / total) * 100) if total > 0 else 0
col4.metric("Balance score", f"{balance}%")

st.divider()

# ---- volume chart ----
st.subheader(f"Muscle group volume, last {window} days")

if session_count == 0:
    st.info("No sessions logged in this window. Try a longer window, or log a session on the 'Log session' page.")
else:
    sorted_muscles = sorted(muscle_groups, key=lambda m: volume[m])
    colors = ["#c98500" if m in neglected else "#2a78d6" for m in sorted_muscles]

    fig = go.Figure(go.Bar(
        x=[volume[m] for m in sorted_muscles],
        y=[m.capitalize() for m in sorted_muscles],
        orientation="h",
        marker_color=colors,
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Volume (weighted movement score)",
    )
    st.plotly_chart(fig, use_container_width=True)

    if neglected:
        names = " & ".join(m.capitalize() for m in neglected)
        st.warning(
            f"**{names}** {'has' if len(neglected) == 1 else 'have'} been trained relatively little in the last {window} days. "
            f"Check the Workout library for workouts that emphasize {'it' if len(neglected) == 1 else 'them'}."
        )

st.caption(
    "Demo data: benchmark and 2025-2026 Open workouts with a synthetic 90-day session log. "
    "Sessions logged on the 'Log session' page persist only for this browser session (not saved to disk)."
)
