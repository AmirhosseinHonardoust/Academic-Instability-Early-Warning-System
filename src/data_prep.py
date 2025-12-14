from __future__ import annotations

import pandas as pd

from . import config
from . import instability


def load_raw() -> pd.DataFrame:
    if not config.DATA_RAW.exists():
        raise FileNotFoundError(f"Raw dataset not found: {config.DATA_RAW}")
    return pd.read_csv(config.DATA_RAW)


def load_processed() -> pd.DataFrame:
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.DATA_PROCESSED_DIR / "academic_instability.parquet"
    if out_path.exists():
        return pd.read_parquet(out_path)

    df = load_raw()

    # Light cleanup
    if config.COL_GENDER in df.columns:
        df[config.COL_GENDER] = df[config.COL_GENDER].astype(str).str.strip()

    # Compute instability
    df = instability.compute_instability(df)

    df.to_parquet(out_path, index=False)
    return df
