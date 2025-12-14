from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from . import config, data_prep


def cmd_prepare_data(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    print(f"Prepared processed dataset with {len(df)} rows.")
    print("Columns:")
    print(", ".join(df.columns))


def _select_row(df, idx: Optional[int], sid: Optional[int]):
    if sid is not None and config.COL_STUDENT_ID in df.columns:
        m = df[df[config.COL_STUDENT_ID] == sid]
        if m.empty:
            raise ValueError(f"No student_id matched: {sid}")
        return m.iloc[0]
    if idx is None:
        raise ValueError("Provide --index or --id")
    if idx < 0 or idx >= len(df):
        raise IndexError(f"Index out of range: {idx}")
    return df.iloc[idx]


def cmd_show_student(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    row = _select_row(df, args.index, args.id)

    print("Student:")
    for c in [config.COL_STUDENT_ID, config.COL_GENDER]:
        if c in row.index:
            print(f"- {c}: {row[c]}")

    print("\nSignals:")
    for c in [config.COL_HOURS, config.COL_ATTEND, config.COL_ASSIGN, config.COL_TEST_SCORE]:
        if c in row.index:
            print(f"- {c}: {row[c]}")

    print("\nPressures:")
    for c in [config.COL_PRESSURE_LOAD, config.COL_PRESSURE_ATTEND, config.COL_PRESSURE_ENGAGE]:
        if c in row.index:
            print(f"- {c}: {float(row[c]):.3f}")

    print("\nOutputs:")
    for c in [config.COL_BUFFER, config.COL_INSTABILITY, config.COL_ZONE]:
        if c in row.index:
            print(f"- {c}: {row[c]}")


def cmd_export_snapshot(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved snapshot to: {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Academic Instability Early Warning System CLI")
    sp = p.add_subparsers(dest="command", required=True)

    p1 = sp.add_parser("prepare-data", help="Compute instability outputs and cache parquet.")
    p1.set_defaults(func=cmd_prepare_data)

    p2 = sp.add_parser("show-student", help="Show details for one student.")
    p2.add_argument("--index", type=int, default=None)
    p2.add_argument("--id", type=int, default=None)
    p2.set_defaults(func=cmd_show_student)

    p3 = sp.add_parser("export-snapshot", help="Export full processed dataset to CSV.")
    p3.add_argument("--out", type=Path, default=config.REPORTS_METRICS_DIR / "instability_snapshot.csv")
    p3.set_defaults(func=cmd_export_snapshot)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
