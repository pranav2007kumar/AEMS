from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[str] = mapped_column(String(40))

class Hostel(Base):
    __tablename__ = 'hostels'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

class Student(Base):
    __tablename__ = 'students'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(100))
    hostel_id: Mapped[str] = mapped_column(ForeignKey('hostels.id'))
    warden_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    sample: Mapped[bool] = mapped_column(Boolean, default=True)

class Gate(Base):
    __tablename__ = 'gates'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

class Visit(Base):
    __tablename__ = 'visits'
    __table_args__ = (
        Index('unique_active_plate_date', 'plate', 'visit_date', unique=True,
            sqlite_where=text("status IN ('pending','approved','inside','exit')"),
            postgresql_where=text("status IN ('pending','approved','inside','exit')")),
        Index('unique_vehicle_inside', 'plate', unique=True,
            sqlite_where=text("status IN ('inside','exit')"),
            postgresql_where=text("status IN ('inside','exit')")),
    )
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visitor_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    relationship: Mapped[str] = mapped_column(String(40))
    vehicle_type: Mapped[str] = mapped_column(String(20))
    plate: Mapped[str] = mapped_column(String(20), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'), index=True)
    purpose: Mapped[str] = mapped_column(String(180))
    visit_date: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    tracking_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))
    entered_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    exited_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entry_person_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_person_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    __mapper_args__ = {'version_id_col': version}

class Approval(Base):
    __tablename__ = 'approvals'
    __table_args__ = (UniqueConstraint('visit_id', 'phase'),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey('visits.id'), index=True)
    phase: Mapped[str] = mapped_column(String(10))
    decision: Mapped[str] = mapped_column(String(10))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String(40))

class Inspection(Base):
    __tablename__ = 'inspections'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey('visits.id'), index=True)
    guard_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(Text, default='')
    confirmed_at: Mapped[str] = mapped_column(String(40))

class GateEvent(Base):
    __tablename__ = 'gate_events'
    __table_args__ = (UniqueConstraint('visit_id', 'direction'),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey('visits.id'), index=True)
    gate_id: Mapped[str] = mapped_column(ForeignKey('gates.id'))
    guard_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    direction: Mapped[str] = mapped_column(String(10))
    original_plate: Mapped[str] = mapped_column(String(30), default='')
    recorded_at: Mapped[str] = mapped_column(String(40))

class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey('visits.id'))
    title: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20))
    owner_role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default='open')
    note: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(150), default='')
    created_at: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {'version_id_col': version}

class IncidentAction(Base):
    __tablename__ = 'incident_actions'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey('incidents.id'))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40))

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    visit_id: Mapped[str | None] = mapped_column(ForeignKey('visits.id'), nullable=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[str] = mapped_column(String(40))

class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class VehicleOccupancy(Base):
    __tablename__ = 'vehicle_occupancy'
    plate: Mapped[str] = mapped_column(String(20), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(40))
    entered_at: Mapped[str] = mapped_column(String(40))
