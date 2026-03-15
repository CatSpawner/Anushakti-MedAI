from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, ConfigDict

Role = Literal["patient", "doctor", "admin"]
Priority = Literal["Low", "Medium", "High", "Emergency"]
AppointmentStatus = Literal["Waiting", "Completed"]
TriageSource = Literal["ai", "ml", "rules"]


class PatientRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Role


class PatientSymptomSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=200)
    symptoms: str = Field(min_length=3, max_length=5000)


class AppointmentCreateResponse(BaseModel):
    appointment_id: int
    assigned_doctor: Optional[str]
    department: str
    severity: int
    priority: Priority
    estimated_waiting_time_minutes: int
    queue_position: int
    status: AppointmentStatus
    triage_source: TriageSource
    ai_guidance: Optional[str] = None


class PatientAppointmentItem(BaseModel):
    appointment_id: int
    created_at: datetime
    status: AppointmentStatus
    department: str
    priority: Priority
    severity: int
    queue_position: int
    estimated_waiting_time_minutes: int
    assigned_doctor: Optional[str]


class PatientDashboardResponse(BaseModel):
    patient: str
    tip: str
    appointments: List[PatientAppointmentItem]


class DoctorAppointmentItem(BaseModel):
    appointment_id: int
    created_at: datetime
    patient_name: str
    department: str
    priority: Priority
    severity: int
    queue_position: int
    predicted_wait_minutes: int
    status: AppointmentStatus


class DoctorDashboardResponse(BaseModel):
    doctor: str
    department: str
    assigned_patients: List[DoctorAppointmentItem]


class DoctorAppointmentDetailResponse(BaseModel):
    appointment_id: int
    created_at: datetime
    status: AppointmentStatus
    patient_name: str
    department: str
    priority: Priority
    severity: int
    queue_position: int
    predicted_wait_minutes: int
    assigned_doctor: Optional[str]
    symptoms: str


class DoctorUpdateAppointmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department: str = Field(min_length=2, max_length=80)
    queue_position: int = Field(ge=1, le=9999)
    predicted_wait_minutes: int = Field(ge=0, le=20000)
    severity: int = Field(ge=1, le=10)
    priority: Priority


class DoctorCompleteAppointmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: bool = True


class DoctorManualReassignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doctor_id: int = Field(ge=1)


class DoctorListItem(BaseModel):
    id: int
    full_name: str
    department: str


# ===== Admin schemas =====
class AdminDoctorCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    department: str = Field(min_length=2, max_length=80)


class AdminDoctorUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=200)
    department: str = Field(min_length=2, max_length=80)


class AdminDoctorPasswordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=8, max_length=128)


class AdminReassignAppointmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appointment_id: int = Field(ge=1)
    new_doctor_id: int = Field(ge=1)