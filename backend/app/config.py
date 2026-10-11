import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'chakrasetu.db'}")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT / "uploads")))
RULE_VERSION = "chakra-1.0"
HOLD_MINUTES = max(1, int(os.getenv("CAPACITY_HOLD_MINUTES", "30")))

import json

TELEMETRY_THRESHOLDS = json.loads(
    os.getenv(
        "TELEMETRY_THRESHOLDS",
        '{"TEMPERATURE":50,"SHOCK":3,"PROLONGED_STOP":30,"ROUTE_DEVIATION":5}',
    )
)

APP_ENV = os.getenv("APP_ENV", "development")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
