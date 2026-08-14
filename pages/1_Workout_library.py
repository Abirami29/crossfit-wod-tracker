import streamlit as st
import plotly.graph_objects as go

from logic.muscle_mapping import load_movements, load_workouts, compute_muscle_load, normalize_load, format_top_muscles
from logic.scoring import workout_status, format_score
from logic.aggregate import load_sessions

st.set_page_config(page_title="Workout library", page_icon="📋", layout="wide")

@st.cache_data
def get_data():
    movement_map, muscle_groups = load_movements()
    workouts = load_workouts()
    sessions = load_sessions()
    return movement_map, muscle_groups, workouts, sessions

movement_map, muscle_groups, workouts, sessions = get_data()
if "logged_sessions" not in st.session_state:
    st.session_state.logged_sessions = []
all_sessions = sessions + st.session_state.logged_sessions

st.title("Workout library")

CATEGORY_LABELS = {"girl": "Girl", "hero": "Hero WOD", "open": "Open"}

col_filters, col_main = st.columns([1, 3])

with col_filters:
    categories = sorted(set(w["category"] for w in workouts))
    selected_categories = st.multiselect(
        "Category", categories, default=categories,
        format_func=lambda c: CATEGORY_LABELS.get(c, c)
    )
    formats = sorted(set(w["format"] for w in workouts))
    selected_formats = st.multiselect("Format", formats, default=formats)

filtered = [w for w in workouts if w["category"] in selected_categories and w["format"] in selected_formats]

if not filtered:
    st.warning("No workouts match these filters — try selecting at least one category and format on the left.")
    st.stop()

with col_filters:
    names = [w["name"] for w in filtered]
    selected_name = st.radio("Workout", names, label_visibility="collapsed")
    selected = next(w for w in filtered if w["name"] == selected_name)

with col_main:
    load, unmatched = compute_muscle_load(selected, movement_map, muscle_groups)
    norm = normalize_load(load)

    header_col, badge_col = st.columns([4, 1])
    header_col.subheader(selected["name"])
    badge_col.markdown(f"<div style='text-align:right'><span style='background:var(--bg-warning,#faeeda); padding:4px 10px; border-radius:6px; font-size:13px;'>{CATEGORY_LABELS.get(selected['category'], selected['category'])}</span></div>", unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Format", selected["format"].replace("_", " ").title())
    m2.metric("Distinct movements", len(set(m["movement"] for m in selected["movements"])))
    m3.metric("Top muscle(s)", format_top_muscles(load))

    if selected.get("rounds"):
        st.caption(f"Structure: {selected['rounds']}" + (f" | Time cap: {selected['time_cap_minutes']} min" if selected.get("time_cap_minutes") else ""))
    elif selected.get("time_cap_minutes"):
        st.caption(f"Time cap: {selected['time_cap_minutes']} min")

    with st.expander("Movement breakdown", expanded=True):
        for m in selected["movements"]:
            reps = f"{m['reps']} " if m.get("reps") is not None else ""
            unit = m.get("unit", "")
            st.write(f"- {reps}{unit} — **{m['movement']}**".replace("  ", " "))

    status = workout_status(selected, all_sessions)
    if status["rx"]["has_pb"]:
        st.success(f"🏆 Your Rx PB: **{status['rx']['pb_display']}** (from {status['rx']['attempt_count']} attempt{'s' if status['rx']['attempt_count'] != 1 else ''})")
    if status["scaled"]["has_pb"]:
        note = " (not directly comparable to Rx benchmark bands)" if status["has_benchmark"] else ""
        st.info(f"Your Scaled PB: **{status['scaled']['pb_display']}** (from {status['scaled']['attempt_count']} attempt{'s' if status['scaled']['attempt_count'] != 1 else ''}){note}")
    if not status["has_any_pb"]:
        if status["has_benchmark"]:
            st.info(
                "You haven't attempted this workout yet. Until you log an Rx score, it'll be evaluated against public "
                "benchmark ranges below — from your next Rx attempt onward, it'll compare against your own Rx PB instead. "
                "Scaled attempts are tracked separately."
            )
            bands = status["bands"]
            band_order = ["elite", "advanced", "intermediate", "beginner"] if selected["lower_is_better"] else ["beginner", "intermediate", "advanced", "elite"]
            cols = st.columns(4)
            for col, level in zip(cols, band_order):
                lo, hi = bands[level]
                col.metric(level.capitalize(), f"{format_score(lo, status['score_type'])}–{format_score(hi, status['score_type'])}")
        else:
            st.info(
                "You haven't attempted this workout yet, and there's no public benchmark data available for it "
                "(Open workouts are leaderboard-scored, not band-scored). Your first logged attempt will become your baseline."
            )

    fig = go.Figure()
    categories_r = [m.capitalize() for m in muscle_groups] + [muscle_groups[0].capitalize()]
    values_r = [norm[m] for m in muscle_groups] + [norm[muscle_groups[0]]]
    fig.add_trace(go.Scatterpolar(r=values_r, theta=categories_r, fill="toself", name=selected["name"], line_color="#d95926"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)),
        showlegend=False,
        height=380,
        margin=dict(l=40, r=40, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    if unmatched:
        st.caption(f"⚠ Movements not yet in the mapping table: {', '.join(unmatched)}")
