from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib

ALLOWED_DEPARTMENTS = {
    "General Medicine","Cardiology","Dermatology","ENT","Paediatrics",
    "Obstetrics & Gynaecology","Orthopaedics","Pulmonology","Ophthalmology",
    "Dental","Endocrinology","Nephrology","Emergency",
}
ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Emergency"}

@dataclass(frozen=True)
class MLTriageResult:
    department: str
    priority: str
    severity_score: int

MODEL_PATH = Path(__file__).resolve().parent / "ml_artifacts" / "triage_model.joblib"

def ml_triage(symptoms: str) -> Optional[MLTriageResult]:
    if not MODEL_PATH.exists():
        return None
    try:
        bundle = joblib.load(MODEL_PATH)
        predictor = bundle["predictor"]
        dept, pri, sev = predictor.predict([symptoms])[0]
        dept = str(dept).strip()
        pri = str(pri).strip()
        sev = int(sev)
        if dept not in ALLOWED_DEPARTMENTS:
            dept = "General Medicine"
        if pri not in ALLOWED_PRIORITIES:
            pri = "Medium"
        sev = max(1, min(10, sev))
        return MLTriageResult(department=dept, priority=pri, severity_score=sev)
    except Exception:
        return None