import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src import config, data_prep, instability


@st.cache_data
def load_df() -> pd.DataFrame:
    return data_prep.load_processed()


def _student_options(df: pd.DataFrame) -> list[str]:
    opts = []
    for i, r in df.reset_index(drop=True).iterrows():
        sid = r.get(config.COL_STUDENT_ID, i)
        g = r.get(config.COL_GENDER, "")
        z = r.get(config.COL_ZONE, "")
        opts.append(f"[{i}] Student {sid} | {g} | {z}")
    return opts


def _pressure_table(row: pd.Series) -> pd.DataFrame:
    labels = [
        ("Cognitive Load", config.COL_PRESSURE_LOAD),
        ("Attendance", config.COL_PRESSURE_ATTEND),
        ("Engagement", config.COL_PRESSURE_ENGAGE),
    ]
    data = []
    for name, col in labels:
        v = float(row.get(col, 0.0))
        data.append({"Pressure": name, "Value": v})
    return pd.DataFrame(data)


def main() -> None:
    st.set_page_config(page_title="Academic Instability Early Warning System", layout="wide")
    st.title("Academic Instability Early Warning System")
    st.caption("Grades are lagging indicators. Instability is the leading signal.")

    df = load_df()
    if df.empty:
        st.error("Processed dataset is empty.")
        return

    tab1, tab2, tab3 = st.tabs(["Student Diagnostic", "Intervention Simulator", "Cohort Map"])

    # ---------------- Student Diagnostic ----------------
    with tab1:
        st.subheader("Student Diagnostic")
        st.markdown(
            "This view explains **why** a student is becoming fragile by decomposing instability into pressures and buffers.\n\n"
            "Interpretation tip: **tension and instability rise before test scores collapse**."
        )

        left, right = st.columns([2, 1])
        with left:
            opts = _student_options(df)
            choice = st.selectbox("Choose a student", opts, index=0)
            idx = int(choice.split(']')[0].replace('[', '').strip())
        with right:
            st.info("Use the Intervention Simulator to test what-if actions and see which lever reduces instability most.")

        row = df.iloc[idx]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Instability Index", f"{float(row[config.COL_INSTABILITY]):.3f}")
        m2.metric("Early-Warning Zone", str(row[config.COL_ZONE]))
        m3.metric("Buffer Strength", f"{float(row[config.COL_BUFFER]):.3f}")
        # test_score is optional benchmark, displayed but not used as model target
        if config.COL_TEST_SCORE in df.columns:
            m4.metric("Observed Test Score", f"{float(row[config.COL_TEST_SCORE]):.1f}")
        else:
            m4.metric("Observed Test Score", "N/A")


        st.markdown("### Pressure Breakdown")
        ptab = _pressure_table(row)
        bar = alt.Chart(ptab).mark_bar().encode(
            x=alt.X("Value:Q", scale=alt.Scale(domain=[-1, 0])),
            y=alt.Y("Pressure:N", sort=None),
            tooltip=["Pressure", "Value"],
        )
        st.altair_chart(bar, use_container_width=True)

        st.markdown("### Explanation (Narrative)")
        st.write(
            "The instability index increases when negative pressures intensify and buffers weaken.\n\n"
            "- **Cognitive Load Pressure** is U-shaped: both very low study time (disengagement) and very high study time (overload) increase instability.\n"
            "- **Attendance Pressure** rises as attendance drops, because the system loses continuity and recovery time.\n"
            "- **Engagement Pressure** rises when assignments completed is low, indicating weak momentum and low feedback frequency.\n\n"
            "Buffer strength summarizes how much consistent attendance and engagement can absorb shocks."
        )

        with st.expander("Raw row (debug)"):
            st.dataframe(pd.DataFrame(row).T)

    # ---------------- Intervention Simulator ----------------
    with tab2:
        st.subheader("Intervention Simulator (What-if)")
        st.markdown(
            "This simulator tests interventions as **counterfactual adjustments** to the same student.\n\n"
            "The purpose is not to predict grades, it's to identify **high-leverage actions** that reduce instability."
        )

        idx = st.number_input("Row index", min_value=0, max_value=int(len(df) - 1), value=0, step=1)
        base_row = df.iloc[int(idx)].copy()

        c1, c2, c3 = st.columns(3)
        with c1:
            hours_delta = st.slider("Change in hours studied (Δ)", -5.0, 5.0, 0.0, 0.1)
        with c2:
            attend_delta = st.slider("Change in attendance % (Δ)", -30.0, 30.0, 0.0, 1.0)
        with c3:
            assign_delta = st.slider("Change in assignments completed (Δ)", -10.0, 10.0, 0.0, 1.0)

        if st.button("Run Intervention"):
            # Rebuild a temporary dataframe to preserve cohort-relative normalization
            df_sim = df.copy()

            # Apply intervention to raw signal columns
            r = base_row.copy()
            if config.COL_HOURS in r.index:
                r[config.COL_HOURS] = float(r[config.COL_HOURS]) + float(hours_delta)
            if config.COL_ATTEND in r.index:
                r[config.COL_ATTEND] = float(r[config.COL_ATTEND]) + float(attend_delta)
            if config.COL_ASSIGN in r.index:
                r[config.COL_ASSIGN] = float(r[config.COL_ASSIGN]) + float(assign_delta)

            df_sim.iloc[int(idx)] = r

            # Recompute instability on the modified dataset
            df_sim = instability.compute_instability(df_sim)

            before = df.iloc[int(idx)]
            after = df_sim.iloc[int(idx)]

            st.markdown("### Results")
            a1, a2, a3 = st.columns(3)
            a1.metric("Instability (Before)", f"{float(before[config.COL_INSTABILITY]):.3f}")
            a2.metric("Instability (After)", f"{float(after[config.COL_INSTABILITY]):.3f}")
            delta = float(after[config.COL_INSTABILITY]) - float(before[config.COL_INSTABILITY])
            a3.metric("Δ Instability", f"{delta:+.3f}")

            st.markdown("### Pressure Comparison")
            comp = pd.DataFrame({
                "Pressure": ["Cognitive Load", "Attendance", "Engagement"],
                "Before": [
                    float(before[config.COL_PRESSURE_LOAD]),
                    float(before[config.COL_PRESSURE_ATTEND]),
                    float(before[config.COL_PRESSURE_ENGAGE]),
                ],
                "After": [
                    float(after[config.COL_PRESSURE_LOAD]),
                    float(after[config.COL_PRESSURE_ATTEND]),
                    float(after[config.COL_PRESSURE_ENGAGE]),
                ],
            })
            st.dataframe(comp)

            st.markdown("### Interpretation")
            st.write(
                "A negative Δ means instability decreased (good).\n\n"
                "Use this to identify which lever reduces instability most for a given student: attendance consistency, engagement momentum, or load normalization."
            )

    # ---------------- Cohort Map ----------------
    with tab3:
        st.subheader("Cohort Instability Map")
        st.markdown(
            "This map shows the cohort as a pressure field.\n\n"
            "- **x-axis:** Buffer Strength (higher = more protective)\n"
            "- **y-axis:** Instability Index (higher = more fragile)\n\n"
            "Clusters reveal where instability accumulates and how buffering distributes across the group."
        )

        # Optional filter by zone
        zones = df[config.COL_ZONE].dropna().unique().tolist()
        zone_filter = st.multiselect("Filter zones", zones, default=zones)

        plot_df = df.copy()
        if zone_filter:
            plot_df = plot_df[plot_df[config.COL_ZONE].isin(zone_filter)]

        chart = alt.Chart(plot_df).mark_circle(size=90).encode(
            x=alt.X(f"{config.COL_BUFFER}:Q", title="Buffer Strength"),
            y=alt.Y(f"{config.COL_INSTABILITY}:Q", title="Instability Index"),
            color=alt.Color(f"{config.COL_ZONE}:N", title="Zone"),
            tooltip=[
                config.COL_STUDENT_ID,
                config.COL_GENDER,
                config.COL_HOURS,
                config.COL_ATTEND,
                config.COL_ASSIGN,
                config.COL_INSTABILITY,
                config.COL_ZONE,
            ],
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

        with st.expander("Show processed data"):
            st.dataframe(plot_df)

if __name__ == "__main__":
    main()
