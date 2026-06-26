"""SQLAlchemy ORM models for PunchPoint."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="company")
    employees = relationship("Employee", back_populates="company")
    projects = relationship("Project", back_populates="company")
    cost_codes = relationship("CostCode", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="worker")  # admin / manager / worker
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    employee_id = Column(String, nullable=False)  # company-internal identifier
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    hourly_rate = Column(Numeric(10, 2), nullable=False, default=0)
    overtime_rate = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="employees")
    user = relationship("User")
    time_entries = relationship("TimeEntry", back_populates="employee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    client_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geofence_radius_meters = Column(Float, default=100)
    budget_hours = Column(Float, nullable=True)
    budget_labor_cost = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="active")  # active / completed
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="projects")
    time_entries = relationship("TimeEntry", back_populates="project")
    photos = relationship("Photo", back_populates="project")
    daily_reports = relationship("DailyReport", back_populates="project")


class CostCode(Base):
    __tablename__ = "cost_codes"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    code = Column(String, nullable=False)
    description = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    company = relationship("Company", back_populates="cost_codes")


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    cost_code_id = Column(Integer, ForeignKey("cost_codes.id"), nullable=True)
    clock_in = Column(DateTime, nullable=False)
    clock_out = Column(DateTime, nullable=True)
    latitude_in = Column(Float, nullable=True)
    longitude_in = Column(Float, nullable=True)
    latitude_out = Column(Float, nullable=True)
    longitude_out = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="time_entries")
    project = relationship("Project", back_populates="time_entries")
    cost_code = relationship("CostCode")
    photos = relationship("Photo", back_populates="time_entry")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    time_entry_id = Column(Integer, ForeignKey("time_entries.id"), nullable=True)
    filename = Column(String, nullable=False)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="photos")
    employee = relationship("Employee")
    time_entry = relationship("TimeEntry", back_populates="photos")


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    date = Column(Date, nullable=False)
    weather = Column(String, nullable=True)
    crew_summary = Column(String, nullable=True)
    hours_total = Column(Float, nullable=True)
    injuries_reported = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="daily_reports")