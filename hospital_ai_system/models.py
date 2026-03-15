from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # patient/doctor/admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    doctor_profile: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="user", uselist=False)
    patient_profile: Mapped[Optional["Patient"]] = relationship("Patient", back_populates="user", uselist=False)


class Doctor(Base):
    __tablename__ = "doctors"
    __table_args__ = (UniqueConstraint("user_id", name="uq_doctors_user_id"), Index("ix_doctors_department", "department"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    max_concurrent: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (UniqueConstraint("user_id", name="uq_patients_user_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="patient_profile")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_status", "status"),
        Index("ix_appointments_department_created_at", "department", "created_at"),
        Index("ix_appointments_doctor_id", "doctor_id"),
        Index("ix_appointments_patient_id", "patient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)

    department: Mapped[str] = mapped_column(String(80), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)

    severity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)

    predicted_wait_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[str] = mapped_column(String(30), default="Waiting", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="appointments")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_appointment_id", "appointment_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)