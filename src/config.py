from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_RAW = BASE_DIR / "data" / "raw" / "student_performance_analysis.csv"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"

REPORTS_DIR = BASE_DIR / "reports"
REPORTS_METRICS_DIR = REPORTS_DIR / "metrics"
REPORTS_FIGURES_DIR = REPORTS_DIR / "figures"

# Column names (as provided in the uploaded CSV)
COL_STUDENT_ID = "student_id"
COL_GENDER = "gender"
COL_HOURS = "hours_studied"
COL_ATTEND = "attendance_percent"
COL_ASSIGN = "assignments_completed"
COL_TEST_SCORE = "test_score"  # optional benchmark, not required for the instability index

# Engineered columns
COL_HOURS_N = "hours_norm"
COL_ATTEND_N = "attendance_norm"
COL_ASSIGN_N = "assignments_norm"

# Pressure components (negative pressures are destabilizing)
COL_PRESSURE_LOAD = "pressure_cognitive_load"
COL_PRESSURE_ATTEND = "pressure_attendance"
COL_PRESSURE_ENGAGE = "pressure_engagement"

# Buffer strength & outputs
COL_BUFFER = "buffer_strength"
COL_INSTABILITY = "instability_index"
COL_ZONE = "early_warning_zone"
