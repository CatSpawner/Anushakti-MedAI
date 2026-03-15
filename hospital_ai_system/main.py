from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from .auth import (
    COOKIE_NAME,
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    create_access_token,
    decode_token,
    get_token_from_cookie,
    hash_password,
    verify_password,
)
from .database import Base, engine, get_db
from .gemini import gemini_triage, GeminiError
from .ml_triage import ml_triage
from .models import Appointment, AuditLog, Doctor, Patient, User
from .schemas import (
    AdminDoctorCreateRequest,
    AdminDoctorPasswordUpdateRequest,
    AdminDoctorUpdateRequest,
    AdminReassignAppointmentRequest,
    AppointmentCreateResponse,
    DoctorAppointmentDetailResponse,
    DoctorCompleteAppointmentRequest,
    DoctorDashboardResponse,
    DoctorListItem,
    DoctorManualReassignRequest,
    DoctorUpdateAppointmentRequest,
    LoginRequest,
    PatientDashboardResponse,
    PatientRegisterRequest,
    PatientSymptomSubmitRequest,
)
from .triage_rules import triage_rules

load_dotenv()

APP_NAME = "Hospital AI System — MSc CS Final Project"
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title=APP_NAME)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(_: Request, __: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many attempts. Please try again later."})


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def require_user(db: Session = Depends(get_db), token: str = Depends(get_token_from_cookie)) -> User:
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(role: str):
    def _dep(user: User = Depends(require_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail="Not allowed")
        return user
    return _dep


def audit(db: Session, *, actor_user_id: int, action: str, detail: dict, appointment_id: Optional[int] = None) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            appointment_id=appointment_id,
            action=action,
            detail_json=json.dumps(detail, ensure_ascii=False),
        )
    )


def seed_initial(db: Session) -> None:
    # Doctors
    if db.query(Doctor).count() == 0:
        seed = [
            ("dr_ashwini", "Doctor@1234", "Dr. Ashwini Kulkarni", "General Medicine"),
            ("dr_rahul", "Doctor@1234", "Dr. Rahul Deshmukh", "Cardiology"),
            ("dr_meera", "Doctor@1234", "Dr. Meera Iyer", "Dermatology"),
            ("dr_sanjay", "Doctor@1234", "Dr. Sanjay Patil", "ENT"),
            ("dr_neha", "Doctor@1234", "Dr. Neha Sharma", "Paediatrics"),
            ("dr_priya", "Doctor@1234", "Dr. Priya Nair", "Obstetrics & Gynaecology"),
            ("dr_omkar", "Doctor@1234", "Dr. Omkar Joshi", "Orthopaedics"),
            ("dr_farhan", "Doctor@1234", "Dr. Farhan Shaikh", "Pulmonology"),
            ("dr_kavita", "Doctor@1234", "Dr. Kavita Rao", "Ophthalmology"),
            ("dr_vivek", "Doctor@1234", "Dr. Vivek Gupta", "Dental"),
            ("dr_anita", "Doctor@1234", "Dr. Anita Sengupta", "Endocrinology"),
            ("dr_rohit", "Doctor@1234", "Dr. Rohit Bhosale", "Nephrology"),
            ("dr_emergency", "Doctor@1234", "Dr. Sameer Khan", "Emergency"),
        ]
        for username, password, full_name, dept in seed:
            u = User(username=username, password_hash=hash_password(password), role="doctor")
            db.add(u)
            db.flush()
            db.add(Doctor(user_id=u.id, full_name=full_name, department=dept, max_concurrent=6))
        db.commit()

    # Single admin
    if not db.query(User).filter(User.username == "aditi").first():
        db.add(User(username="aditi", password_hash=hash_password("Aditi#@!123"), role="admin"))
        db.commit()


Base.metadata.create_all(bind=engine)
_db = next(get_db())
try:
    seed_initial(_db)
finally:
    _db.close()


# Pages
@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "app_name": APP_NAME})


@app.get("/patient", response_class=HTMLResponse)
def patient_portal(request: Request):
    return templates.TemplateResponse("patient.html", {"request": request, "app_name": APP_NAME})


@app.get("/doctor", response_class=HTMLResponse)
def doctor_portal(request: Request):
    return templates.TemplateResponse("doctor.html", {"request": request, "app_name": APP_NAME})


@app.get("/admin", response_class=HTMLResponse)
def admin_portal(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request, "app_name": APP_NAME})


# Common API
@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}


@app.post("/register/patient", status_code=201)
def register_patient(req: PatientRegisterRequest, db: Session = Depends(get_db)):
    u = User(username=req.username, password_hash=hash_password(req.password), role="patient")
    db.add(u)
    try:
        db.flush()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    db.add(Patient(user_id=u.id, full_name=req.full_name))
    db.commit()
    return {"message": "registered"}


@app.post("/login")
@limiter.limit("10/minute")
def login(request: Request, req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == req.username, User.is_active == True).first()  # noqa: E712
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if u.role != req.role:
        raise HTTPException(status_code=403, detail="Please select the correct role.")

    token = create_access_token(sub=u.username, role=u.role)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=7200,
        path="/",
    )
    return {"message": "logged_in", "role": u.role}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "logged_out"}


@app.get("/me")
def me(user: User = Depends(require_user)):
    return {"username": user.username, "role": user.role}


# Patient APIs
@app.post("/patient/submit", response_model=AppointmentCreateResponse)
def patient_submit(req: PatientSymptomSubmitRequest, user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    patient.full_name = req.name.strip()

    triage_source = "rules"
    ai_guidance: Optional[str] = None

    try:
        ai = gemini_triage(req.symptoms)
        department, severity, priority = ai.department, int(ai.severity_score), str(ai.priority)
        ai_guidance = ai.guidance
        triage_source = "ai"
    except GeminiError:
        ml = ml_triage(req.symptoms)
        if ml:
            department, severity, priority = ml.department, int(ml.severity_score), str(ml.priority)
            triage_source = "ml"
        else:
            t = triage_rules(req.symptoms)
            department, severity, priority = str(t["department"]), int(t["severity_score"]), str(t["priority"])
            triage_source = "rules"

    # Assign any active doctor in that department
    doc = (
        db.query(Doctor)
        .join(User, User.id == Doctor.user_id)
        .filter(Doctor.department == department, User.is_active == True)  # noqa: E712
        .order_by(Doctor.id.asc())
        .first()
    )
    if not doc:
        doc = (
            db.query(Doctor)
            .join(User, User.id == Doctor.user_id)
            .filter(Doctor.department == "General Medicine", User.is_active == True)  # noqa: E712
            .order_by(Doctor.id.asc())
            .first()
        )
    if not doc:
        raise HTTPException(status_code=500, detail="No active doctors available")

    active_count = db.query(Appointment).filter(Appointment.doctor_id == doc.id, Appointment.status == "Waiting").count()
    queue_position = int(active_count) + 1
    predicted_wait = max(10, queue_position * 12)

    appt = Appointment(
        appointment_token=secrets.token_hex(16),
        patient_id=patient.id,
        doctor_id=doc.id,
        department=department,
        symptoms=req.symptoms,
        severity_score=severity,
        priority=priority,
        predicted_wait_minutes=predicted_wait,
        queue_position=queue_position,
        status="Waiting",
        created_at=now_utc(),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return AppointmentCreateResponse(
        appointment_id=appt.id,
        assigned_doctor=doc.full_name,
        department=appt.department,
        severity=appt.severity_score,
        priority=appt.priority,  # type: ignore[arg-type]
        estimated_waiting_time_minutes=appt.predicted_wait_minutes,
        queue_position=appt.queue_position,
        status=appt.status,  # type: ignore[arg-type]
        triage_source=triage_source,  # type: ignore[arg-type]
        ai_guidance=ai_guidance,
    )


@app.get("/patient/dashboard", response_model=PatientDashboardResponse)
def patient_dashboard(user: User = Depends(require_role("patient")), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient profile not found")

    appts = db.query(Appointment).filter(Appointment.patient_id == patient.id).order_by(Appointment.created_at.desc()).limit(25).all()

    items = []
    for a in appts:
        doc = db.query(Doctor).filter(Doctor.id == a.doctor_id).first()
        items.append({
            "appointment_id": a.id,
            "created_at": a.created_at,
            "status": a.status,
            "department": a.department,
            "priority": a.priority,
            "severity": a.severity_score,
            "queue_position": a.queue_position,
            "estimated_waiting_time_minutes": a.predicted_wait_minutes,
            "assigned_doctor": doc.full_name if doc else None,
        })

    tip = "General guidance only. If severe symptoms occur (chest pain, breathlessness, heavy bleeding) seek emergency care."
    return {"patient": patient.full_name, "tip": tip, "appointments": items}


# Doctor APIs
@app.get("/doctor/dashboard", response_model=DoctorDashboardResponse)
def doctor_dashboard(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    appts = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.status == "Waiting").order_by(Appointment.created_at.asc()).all()
    items = []
    for a in appts:
        p = db.query(Patient).filter(Patient.id == a.patient_id).first()
        items.append({
            "appointment_id": a.id,
            "created_at": a.created_at,
            "patient_name": p.full_name if p else "Unknown",
            "department": a.department,
            "priority": a.priority,
            "severity": a.severity_score,
            "queue_position": a.queue_position,
            "predicted_wait_minutes": a.predicted_wait_minutes,
            "status": a.status,
        })
    return {"doctor": doctor.full_name, "department": doctor.department, "assigned_patients": items}


@app.get("/doctor/doctors", response_model=list[DoctorListItem])
def doctor_list_doctors(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    docs = (
        db.query(Doctor, User)
        .join(User, User.id == Doctor.user_id)
        .filter(User.is_active == True)  # noqa: E712
        .order_by(Doctor.department.asc(), Doctor.full_name.asc())
        .all()
    )
    return [{"id": d.id, "full_name": d.full_name, "department": d.department} for d, _ in docs]


@app.get("/doctor/appointments/{appointment_id}", response_model=DoctorAppointmentDetailResponse)
def doctor_get_appointment_detail(appointment_id: int, user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    p = db.query(Patient).filter(Patient.id == appt.patient_id).first()
    doc = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first() if appt.doctor_id else None

    return DoctorAppointmentDetailResponse(
        appointment_id=appt.id,
        created_at=appt.created_at,
        status=appt.status,  # type: ignore[arg-type]
        patient_name=p.full_name if p else "Unknown",
        department=appt.department,
        priority=appt.priority,  # type: ignore[arg-type]
        severity=appt.severity_score,
        queue_position=appt.queue_position,
        predicted_wait_minutes=appt.predicted_wait_minutes,
        assigned_doctor=doc.full_name if doc else None,
        symptoms=appt.symptoms,
    )


@app.put("/doctor/appointments/{appointment_id}")
def doctor_update_appointment(appointment_id: int, req: DoctorUpdateAppointmentRequest, user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    before = {"department": appt.department, "queue_position": appt.queue_position, "predicted_wait_minutes": appt.predicted_wait_minutes, "severity_score": appt.severity_score, "priority": appt.priority}

    appt.department = req.department
    appt.queue_position = int(req.queue_position)
    appt.predicted_wait_minutes = int(req.predicted_wait_minutes)
    appt.severity_score = int(req.severity)
    appt.priority = str(req.priority)

    audit(db, actor_user_id=user.id, action="doctor_update", appointment_id=appt.id, detail={"before": before, "after": {
        "department": appt.department,
        "queue_position": appt.queue_position,
        "predicted_wait_minutes": appt.predicted_wait_minutes,
        "severity_score": appt.severity_score,
        "priority": appt.priority,
    }})

    db.commit()
    return {"message": "updated"}


@app.post("/doctor/appointments/{appointment_id}/complete")
def doctor_complete_appointment(appointment_id: int, _: DoctorCompleteAppointmentRequest, user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    appt.status = "Completed"
    appt.completed_at = now_utc()

    audit(db, actor_user_id=user.id, action="doctor_complete", appointment_id=appt.id, detail={"status": "Completed"})
    db.commit()
    return {"message": "completed"}


@app.post("/doctor/appointments/{appointment_id}/manual_reassign")
def doctor_manual_reassign(appointment_id: int, req: DoctorManualReassignRequest, user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found")

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    new_doc = db.query(Doctor).filter(Doctor.id == req.doctor_id).first()
    if not new_doc:
        raise HTTPException(status_code=404, detail="Doctor not found")

    before = {"doctor_id": appt.doctor_id, "department": appt.department}
    appt.doctor_id = new_doc.id
    appt.department = new_doc.department

    audit(db, actor_user_id=user.id, action="doctor_reassign", appointment_id=appt.id, detail={"before": before, "after": {"doctor_id": appt.doctor_id, "department": appt.department}})
    db.commit()
    return {"message": "reassigned", "new_doctor": new_doc.full_name, "department": new_doc.department}


# =====================
# Admin APIs (detailed)
# =====================
@app.get("/admin/doctors")
def admin_list_doctors(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    docs = db.query(Doctor, User).join(User, User.id == Doctor.user_id).order_by(Doctor.department.asc(), Doctor.full_name.asc()).all()
    out = []
    for d, u in docs:
        waiting = db.query(Appointment).filter(Appointment.doctor_id == d.id, Appointment.status == "Waiting").count()
        completed = db.query(Appointment).filter(Appointment.doctor_id == d.id, Appointment.status == "Completed").count()
        out.append({
            "doctor_id": d.id,
            "user_id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "full_name": d.full_name,
            "department": d.department,
            "waiting_count": waiting,
            "completed_count": completed,
            "created_at": d.created_at.isoformat(),
        })
    return out


@app.get("/admin/doctors/{doctor_id}")
def admin_doctor_detail(doctor_id: int, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    u = db.query(User).filter(User.id == d.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Doctor user not found")

    appts = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == d.id)
        .order_by(Appointment.created_at.desc())
        .limit(200)
        .all()
    )

    rows = []
    for a in appts:
        p = db.query(Patient).filter(Patient.id == a.patient_id).first()
        rows.append({
            "appointment_id": a.id,
            "created_at": a.created_at.isoformat(),
            "status": a.status,
            "department": a.department,
            "priority": a.priority,
            "severity": a.severity_score,
            "queue_position": a.queue_position,
            "predicted_wait_minutes": a.predicted_wait_minutes,
            "patient_name": p.full_name if p else "Unknown",
            "symptoms": a.symptoms,
        })

    return {
        "doctor": {
            "doctor_id": d.id,
            "user_id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "full_name": d.full_name,
            "department": d.department,
            "created_at": d.created_at.isoformat(),
        },
        "appointments": rows,
    }


@app.post("/admin/doctors")
def admin_create_doctor(req: AdminDoctorCreateRequest, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    u = User(username=req.username, password_hash=hash_password(req.password), role="doctor", is_active=True)
    db.add(u)
    try:
        db.flush()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")

    d = Doctor(user_id=u.id, full_name=req.full_name, department=req.department, max_concurrent=6)
    db.add(d)

    audit(db, actor_user_id=user.id, action="admin_create_doctor", detail={"username": req.username, "full_name": req.full_name, "department": req.department}, appointment_id=None)
    db.commit()
    return {"message": "created", "doctor_id": d.id}


@app.put("/admin/doctors/{doctor_id}")
def admin_update_doctor(doctor_id: int, req: AdminDoctorUpdateRequest, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    before = {"full_name": d.full_name, "department": d.department}
    d.full_name = req.full_name
    d.department = req.department

    audit(db, actor_user_id=user.id, action="admin_update_doctor", detail={"doctor_id": doctor_id, "before": before, "after": {"full_name": d.full_name, "department": d.department}}, appointment_id=None)
    db.commit()
    return {"message": "updated"}


@app.put("/admin/doctors/{doctor_id}/password")
def admin_update_doctor_password(doctor_id: int, req: AdminDoctorPasswordUpdateRequest, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    u = db.query(User).filter(User.id == d.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Doctor user not found")

    u.password_hash = hash_password(req.password)
    audit(db, actor_user_id=user.id, action="admin_update_doctor_password", detail={"doctor_id": doctor_id}, appointment_id=None)
    db.commit()
    return {"message": "password_updated"}


@app.post("/admin/doctors/{doctor_id}/deactivate")
def admin_deactivate_doctor(doctor_id: int, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    d = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor not found")
    u = db.query(User).filter(User.id == d.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Doctor user not found")

    u.is_active = False
    audit(db, actor_user_id=user.id, action="admin_deactivate_doctor", detail={"doctor_id": doctor_id, "username": u.username}, appointment_id=None)
    db.commit()
    return {"message": "deactivated"}


@app.post("/admin/reassign")
def admin_reassign_appointment(req: AdminReassignAppointmentRequest, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.id == req.appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    new_doc = db.query(Doctor).filter(Doctor.id == req.new_doctor_id).first()
    if not new_doc:
        raise HTTPException(status_code=404, detail="New doctor not found")

    new_doc_user = db.query(User).filter(User.id == new_doc.user_id).first()
    if not new_doc_user or not new_doc_user.is_active:
        raise HTTPException(status_code=400, detail="New doctor is inactive")

    before = {"doctor_id": appt.doctor_id, "department": appt.department}
    appt.doctor_id = new_doc.id
    appt.department = new_doc.department

    audit(db, actor_user_id=user.id, action="admin_reassign_appointment", appointment_id=appt.id, detail={"before": before, "after": {"doctor_id": appt.doctor_id, "department": appt.department}})
    db.commit()
    return {"message": "reassigned"}


@app.get("/admin/appointments")
def admin_all_appointments(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    appts = db.query(Appointment).order_by(Appointment.created_at.desc()).limit(500).all()
    out = []
    for a in appts:
        p = db.query(Patient).filter(Patient.id == a.patient_id).first()
        d = db.query(Doctor).filter(Doctor.id == a.doctor_id).first() if a.doctor_id else None
        out.append({
            "appointment_id": a.id,
            "created_at": a.created_at.isoformat(),
            "status": a.status,
            "department": a.department,
            "priority": a.priority,
            "severity": a.severity_score,
            "queue_position": a.queue_position,
            "predicted_wait_minutes": a.predicted_wait_minutes,
            "patient_name": p.full_name if p else "Unknown",
            "doctor_name": d.full_name if d else None,
            "symptoms": a.symptoms,
        })
    return out


@app.get("/admin/audit_logs")
def admin_audit_logs(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(300).all()
    out = []
    for l in logs:
        actor = db.query(User).filter(User.id == l.actor_user_id).first()
        out.append({
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "actor": actor.username if actor else f"user#{l.actor_user_id}",
            "action": l.action,
            "appointment_id": l.appointment_id,
            "detail": json.loads(l.detail_json or "{}"),
        })
    return out