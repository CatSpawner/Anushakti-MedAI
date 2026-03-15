from __future__ import annotations

def triage_rules(symptoms: str) -> dict[str, object]:
    s = (symptoms or "").lower()

    if any(k in s for k in ["chest pain", "stroke", "unconscious", "seizure", "severe bleeding"]):
        return {"department": "Emergency", "severity_score": 10, "priority": "Emergency"}

    if any(k in s for k in ["shortness of breath", "breathing", "accident", "burn", "fracture", "high fever"]):
        return {"department": "Emergency", "severity_score": 8, "priority": "High"}

    if any(k in s for k in ["heart", "bp", "palpitation"]):
        return {"department": "Cardiology", "severity_score": 7, "priority": "High"}

    if any(k in s for k in ["skin", "rash", "itch", "acne", "eczema"]):
        return {"department": "Dermatology", "severity_score": 4, "priority": "Medium"}

    if any(k in s for k in ["ear", "throat", "sinus", "nose"]):
        return {"department": "ENT", "severity_score": 4, "priority": "Medium"}

    if any(k in s for k in ["pregnant", "pregnancy", "bleeding"]):
        return {"department": "Obstetrics & Gynaecology", "severity_score": 8, "priority": "Emergency"}

    if any(k in s for k in ["child", "baby", "infant"]):
        return {"department": "Paediatrics", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["asthma", "cough", "lungs", "pneumonia"]):
        return {"department": "Pulmonology", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["eye", "vision", "blur"]):
        return {"department": "Ophthalmology", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["tooth", "dental", "gum"]):
        return {"department": "Dental", "severity_score": 3, "priority": "Low"}

    if any(k in s for k in ["diabetes", "thyroid"]):
        return {"department": "Endocrinology", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["kidney", "urine", "uti"]):
        return {"department": "Nephrology", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["bone", "joint", "knee", "back pain"]):
        return {"department": "Orthopaedics", "severity_score": 5, "priority": "Medium"}

    if any(k in s for k in ["fever", "headache", "vomit", "nausea", "fatigue", "cold"]):
        return {"department": "General Medicine", "severity_score": 4, "priority": "Medium"}

    return {"department": "General Medicine", "severity_score": 3, "priority": "Low"}