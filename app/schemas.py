"""Pydantic v2 schemas for PunchPoint request/response validation."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class AuthRegister(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class AuthLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="worker", pattern="^(admin|manager|worker)$")
    company_id: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    company_id: int
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------
class EmployeeCreate(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    hourly_rate: float = Field(default=0.0, ge=0)
    overtime_rate: float = Field(default=0.0, ge=0)
    is_active: bool = True


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    user_id: Optional[int] = None
    employee_id: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    hourly_rate: float
    overtime_rate: float
    is_active: bool
    created_at: datetime


class EmployeeBulkImportItem(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=64)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    hourly_rate: float = Field(default=0.0, ge=0)
    overtime_rate: float = Field(default=0.0, ge=0)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: float = Field(default=100.0, gt=0)
    budget_hours: Optional[float] = Field(default=None, ge=0)
    budget_labor_cost: Optional[float] = Field(default=None, ge=0)
    status: str = Field(default="active", pattern="^(active|completed)$")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    client_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius_meters: float
    budget_hours: Optional[float] = None
    budget_labor_cost: Optional[float] = None
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Cost Code
# ---------------------------------------------------------------------------
class CostCodeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    description: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True


class CostCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    description: str
    is_active: bool


# ---------------------------------------------------------------------------
# Time Entry
# ---------------------------------------------------------------------------
class TimeEntryCreate(BaseModel):
    employee_id: int
    project_id: int
    cost_code_id: Optional[int] = None
    latitude_in: Optional[float] = None
    longitude_in: Optional[float] = None
    notes: Optional[str] = None


class TimeEntryClockOut(BaseModel):
    employee_id: int
    latitude_out: Optional[float] = None
    longitude_out: Optional[float] = None
    notes: Optional[str] = None


class TimeEntryUpdate(BaseModel):
    clock_out: Optional[datetime] = None
    latitude_out: Optional[float] = None
    longitude_out: Optional[float] = None
    notes: Optional[str] = None
    is_approved: Optional[bool] = None
    cost_code_id: Optional[int] = None


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    project_id: int
    cost_code_id: Optional[int] = None
    clock_in: datetime
    clock_out: Optional[datetime] = None
    latitude_in: Optional[float] = None
    longitude_in: Optional[float] = None
    latitude_out: Optional[float] = None
    longitude_out: Optional[float] = None
    notes: Optional[str] = None
    is_approved: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Photo
# ---------------------------------------------------------------------------
class PhotoUpload(BaseModel):
    project_id: int
    employee_id: int
    time_entry_id: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    timestamp: datetime


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    employee_id: int
    time_entry_id: Optional[int] = None
    filename: str
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    timestamp: datetime
    uploaded_at: datetime


# ---------------------------------------------------------------------------
# Daily Report
# ---------------------------------------------------------------------------
class DailyReportCreate(BaseModel):
    project_id: int
    date: date
    weather: Optional[str] = None
    crew_summary: Optional[str] = None
    hours_total: Optional[float] = Field(default=None, ge=0)
    injuries_reported: Optional[str] = Field(default="None", max_length=500)
    notes: Optional[str] = None


class DailyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    date: date
    weather: Optional[str] = None
    crew_summary: Optional[str] = None
    hours_total: Optional[float] = None
    injuries_reported: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard & Job Costing
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    active_crew: int = 0
    hours_today: float = 0.0
    projects_active: int = 0
    labor_cost_today: float = 0.0


class JobCostingRow(BaseModel):
    project_id: int
    project_name: str
    budget_hours: float = 0.0
    actual_hours: float = 0.0
    budget_labor_cost: float = 0.0
    actual_labor_cost: float = 0.0
    variance_hours: float = 0.0
    variance_cost: float = 0.0
    pct_budget_used: float = 0.0


class JobCostingResponse(BaseModel):
    projects: list[JobCostingRow] = []