import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta

from logic.muscle_mapping import load_movements, load_workouts
from logic.aggregate import load_sessions, aggregate_volume, classify_tiers

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

DEMO_TODAY = date(2026, 8, 13)  # anchor date matching the sample log; a live app would use date.today()
if "dashboard_as_of" not in st.session_state:
    st.session_state.dashboard_as_of = DEMO_TODAY

st.title("Your training balance")

window = st.radio("Window", [7, 30, 90], index=1, format_func=lambda d: f"{d} days", horizontal=True, label_visibility="collapsed")

# ---- date navigation: step the window backward/forward, or jump to today ----
nav_prev, nav_label, nav_next, nav_today = st.columns([1, 3, 1, 1])
if nav_prev.button("← Previous", use_container_width=True):
    st.session_state.dashboard_as_of -= timedelta(days=window)
at_latest = st.session_state.dashboard_as_of >= DEMO_TODAY
if nav_next.button("Next →", use_container_width=True, disabled=at_latest):
    st.session_state.dashboard_as_of = min(st.session_state.dashboard_as_of + timedelta(days=window), DEMO_TODAY)
if nav_today.button("Today", use_container_width=True, disabled=at_latest):
    st.session_state.dashboard_as_of = DEMO_TODAY

AS_OF = st.session_state.dashboard_as_of
window_start = AS_OF - timedelta(days=window)
nav_label.markdown(f"<div style='text-align:center; padding-top:6px;'>{window_start.strftime('%b %-d')} – {AS_OF.strftime('%b %-d, %Y')}</div>", unsafe_allow_html=True)

volume, session_count = aggregate_volume(all_sessions, workouts_by_id, movement_map, muscle_groups, window, AS_OF)
tiers = classify_tiers(volume)
neglected = [m for m, t in tiers.items() if t == "neglected"]

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
st.subheader(f"Muscle group volume, {window_start.strftime('%b %-d')} – {AS_OF.strftime('%b %-d')}")

if session_count == 0:
    st.info("No sessions in this window. Try a different window or use ← Previous to look at an earlier period.")
else:
    TIER_COLORS = {"top": "#0F6E56", "moderate": "#5F5E5A", "neglected": "#BA7517"}
    sorted_muscles = sorted(muscle_groups, key=lambda m: volume[m])
    values = [volume[m] for m in sorted_muscles]
    colors = [TIER_COLORS[tiers[m]] for m in sorted_muscles]
    avg = sum(values) / len(values) if values else 0

    fig = go.Figure(go.Bar(
        x=values,
        y=[m.capitalize() for m in sorted_muscles],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.0f}" for v in values],
        textposition="outside",
        textfont=dict(size=12, color="#5F5E5A"),
        cliponaxis=False,
    ))
    fig.add_vline(x=avg, line_width=1, line_dash="dot", line_color="#B4B2A9")
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis_title="Volume (weighted movement score)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E1E0D9", zeroline=False),
        yaxis=dict(showgrid=False),
        font=dict(family="sans-serif", size=13),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "<div style='display:flex; gap:20px; font-size:12px; color:#5F5E5A; margin-top:-8px;'>"
        "<span><span style='color:#0F6E56'>&#9632;</span> Well trained</span>"
        "<span><span style='color:#5F5E5A'>&#9632;</span> Moderate</span>"
        "<span><span style='color:#BA7517'>&#9632;</span> Neglected</span>"
        "<span style='color:#B4B2A9'>┊ average</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if neglected:
        names = " & ".join(m.capitalize() for m in neglected)
        st.warning(
            f"**{names}** {'has' if len(neglected) == 1 else 'have'} been trained relatively little in this window. "
            f"Check the Workout library for workouts that emphasize {'it' if len(neglected) == 1 else 'them'}."
        )

st.caption(
    "Demo data: benchmark and 2025-2026 Open workouts with a synthetic 90-day session log. "
    "Sessions logged on the 'Log session' page persist only for this browser session (not saved to disk)."
)
