from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash").strip()

ALLOWED_DEPARTMENTS = {
    "General Medicine","Cardiology","Dermatology","ENT","Paediatrics",
    "Obstetrics & Gynaecology","Orthopaedics","Pulmonology","Ophthalmology",
    "Dental","Endocrinology","Nephrology","Emergency",
}
ALLOWED_PRIORITIES = {"Low", "Medium", "High", "Emergency"}


@dataclass(frozen=True)
class AITriageResult:
    department: str
    priority: str
    severity_score: int
    guidance: str


class GeminiError(RuntimeError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise GeminiError("Empty Gemini response")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise GeminiError("No JSON found in response")
    return json.loads(text[s : e + 1])


def gemini_triage(symptoms: str, *, model: Optional[str] = None) -> AITriageResult:
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY missing")

    client = genai.Client(api_key=GEMINI_API_KEY)
    model_name = model or GEMINI_MODEL

    prompt = f"""
Return STRICT JSON only with keys: department, priority, severity_score, guidance.
department must be one of: {sorted(ALLOWED_DEPARTMENTS)}
priority must be one of: {sorted(ALLOWED_PRIORITIES)}
severity_score must be integer 1..10
No diagnosis. No medication dosages.

Symptoms:
{symptoms}
""".strip()

    resp = client.models.generate_content(model=model_name, contents=prompt)
    obj = _extract_json(resp.text or "")

    dept = str(obj.get("department", "General Medicine")).strip()
    if dept not in ALLOWED_DEPARTMENTS:
        dept = "General Medicine"

    pri = str(obj.get("priority", "Medium")).strip()
    if pri not in ALLOWED_PRIORITIES:
        pri = "Medium"

    sev = int(obj.get("severity_score", 5))
    sev = max(1, min(10, sev))

    guidance = str(obj.get("guidance", "")).strip() or "Please wait for your turn. Seek urgent care if symptoms worsen."
    return AITriageResult(department=dept, priority=pri, severity_score=sev, guidance=guidance)