from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _minmax01(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    if s.nunique(dropna=True) <= 1:
        return pd.Series(0.5, index=s.index)
    mn, mx = float(np.nanmin(s)), float(np.nanmax(s))
    if mx - mn == 0:
        return pd.Series(0.5, index=s.index)
    return ((s - mn) / (mx - mn)).clip(0.0, 1.0)


def _robust_z(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    med = s.median()
    mad = (s - med).abs().median()
    if mad == 0 or np.isnan(mad):
        std = s.std()
        if std == 0 or np.isnan(std):
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std
    return (s - med) / (1.4826 * mad)


def compute_instability(df: pd.DataFrame) -> pd.DataFrame:
    """Compute an interpretable Academic Instability Index (AII).

    Design goals:
    - Do NOT predict grades.
    - Use observable conditions as pressures and buffers.
    - Produce a leading-signal 'instability_index' and a zone label.
    """
    df = df.copy()

    # Ensure numeric
    for c in [config.COL_HOURS, config.COL_ATTEND, config.COL_ASSIGN, config.COL_TEST_SCORE]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Normalized scales (0..1)
    df[config.COL_HOURS_N] = _minmax01(df[config.COL_HOURS])
    df[config.COL_ATTEND_N] = _minmax01(df[config.COL_ATTEND])
    df[config.COL_ASSIGN_N] = _minmax01(df[config.COL_ASSIGN])

    # --- Pressure components ---
    # Cognitive load: instability rises when study time is far from the cohort “typical” level.
    # This makes it U-shaped: too low can mean disengagement; too high can mean overload.
    z_hours = _robust_z(df[config.COL_HOURS])
    df[config.COL_PRESSURE_LOAD] = -np.tanh(np.abs(z_hours) / 2.0)  # in [-1, 0], more negative => more pressure

    # Attendance pressure: low attendance creates negative stability pressure
    df[config.COL_PRESSURE_ATTEND] = -(1.0 - df[config.COL_ATTEND_N]).clip(0.0, 1.0)

    # Engagement pressure: low assignment completion creates negative stability pressure
    df[config.COL_PRESSURE_ENGAGE] = -(1.0 - df[config.COL_ASSIGN_N]).clip(0.0, 1.0)

    # Buffer strength: combined capacity to absorb shocks (attendance + engagement)
    df[config.COL_BUFFER] = (0.55 * df[config.COL_ATTEND_N] + 0.45 * df[config.COL_ASSIGN_N]).clip(0.0, 1.0)

    # --- Instability Index ---
    # Instability increases with:
    # - magnitude of negative pressures
    # - conflict/imbalance between pressures (variance)
    # - weak buffers
    pressures = df[[config.COL_PRESSURE_LOAD, config.COL_PRESSURE_ATTEND, config.COL_PRESSURE_ENGAGE]].fillna(0.0)
    neg_mag = (-pressures).mean(axis=1)  # 0..1
    imbalance = pressures.std(axis=1).fillna(0.0)  # 0..~
    weak_buffer = (1.0 - df[config.COL_BUFFER]).clip(0.0, 1.0)

    # Weighted combination (keep in 0..1.5 range for interpretability)
    df[config.COL_INSTABILITY] = (0.55 * neg_mag + 0.20 * imbalance + 0.25 * weak_buffer).clip(0.0, 1.5)

    # --- Early warning zones (quantile-based, dataset-relative) ---
    q1 = df[config.COL_INSTABILITY].quantile(0.50)
    q2 = df[config.COL_INSTABILITY].quantile(0.75)
    q3 = df[config.COL_INSTABILITY].quantile(0.90)

    def zone(v: float) -> str:
        if v <= q1:
            return "🟢 Stable"
        if v <= q2:
            return "🟡 Fragile"
        if v <= q3:
            return "🟠 Unstable"
        return "🔴 Critical"

    df[config.COL_ZONE] = df[config.COL_INSTABILITY].astype(float).apply(zone)

    return df


def apply_intervention_to_row(row: pd.Series, hours_delta: float = 0.0, attendance_delta: float = 0.0, assignments_delta: float = 0.0) -> pd.Series:
    """Apply a hypothetical intervention to a single student row."""
    r = row.copy()
    if config.COL_HOURS in r.index and pd.notna(r[config.COL_HOURS]):
        r[config.COL_HOURS] = float(r[config.COL_HOURS]) + hours_delta
    if config.COL_ATTEND in r.index and pd.notna(r[config.COL_ATTEND]):
        r[config.COL_ATTEND] = float(r[config.COL_ATTEND]) + attendance_delta
    if config.COL_ASSIGN in r.index and pd.notna(r[config.COL_ASSIGN]):
        r[config.COL_ASSIGN] = float(r[config.COL_ASSIGN]) + assignments_delta
    return r
