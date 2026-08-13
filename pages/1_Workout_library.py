import streamlit as st
import plotly.graph_objects as go

from logic.muscle_mapping import load_movements, load_workouts, compute_muscle_load, normalize_load, format_top_muscles

st.set_page_config(page_title="Workout library", page_icon="📋", layout="wide")

@st.cache_data
def get_data():
    movement_map, muscle_groups = load_movements()
    workouts = load_workouts()
    return movement_map, muscle_groups, workouts

movement_map, muscle_groups, workouts = get_data()

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