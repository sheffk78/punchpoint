"""Time tracking router: clock-in, clock-out, entries CRUD, and approval."""

import math
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Employee, Project, CostCode, TimeEntry
from app.schemas import (
    TimeEntryCreate,
    TimeEntryClockOut,
    TimeEntryResponse,
    TimeEntryUpdate,
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/time", tags=["time"])


# --- Utility -----------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two GPS points in meters using the haversine formula."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _get_employee_for_company(
    db: Session, employee_id: int, company_id: int
) -> Employee:
    """Return an Employee owned by *company_id* or raise 404."""
    stmt = select(Employee).where(
        Employee.id == employee_id, Employee.company_id == company_id
    )
    emp = db.execute(stmt).scalar_one_or_none()
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company.",
        )
    return emp


def _get_project_for_company(
    db: Session, project_id: int, company_id: int
) -> Project:
    """Return a Project owned by *company_id* or raise 404."""
    stmt = select(Project).where(
        Project.id == project_id, Project.company_id == company_id
    )
    proj = db.execute(stmt).scalar_one_or_none()
    if proj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your company.",
        )
    return proj


def _get_time_entry_for_company(
    db: Session, entry_id: int, company_id: int
) -> TimeEntry:
    """Return a TimeEntry that belongs to *company_id* (via employee) or raise 404."""
    stmt = (
        select(TimeEntry)
        .join(Employee, TimeEntry.employee_id == Employee.id)
        .where(TimeEntry.id == entry_id, Employee.company_id == company_id)
    )
    entry = db.execute(stmt).scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found in your company.",
        )
    return entry


def _calc_hours(clock_in: datetime, clock_out: datetime) -> float:
    """Hours worked (rounded to 2 decimals)."""
    delta = clock_out - clock_in
    return round(delta.total_seconds() / 3600, 2)


# --- Clock in ----------------------------------------------------------------

@router.post("/clock-in", response_model=TimeEntryResponse, status_code=201)
def clock_in(
    payload: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    employee = _get_employee_for_company(db, payload.employee_id, company_id)
    project = _get_project_for_company(db, payload.project_id, company_id)

    # Reject if employee already has an open entry (clock_out is None).
    open_entry = db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == employee.id,
            TimeEntry.clock_out.is_(None),
        )
    ).scalar_one_or_none()
    if open_entry is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee already has an open time entry. Clock out first.",
        )

    # Geofence check (skip if project has no coordinates or no GPS in payload)
    if project.latitude is not None and project.longitude is not None and payload.latitude_in is not None and payload.longitude_in is not None:
        distance = haversine(
            payload.latitude_in,
            payload.longitude_in,
            project.latitude,
            project.longitude,
        )
        geofence_radius = project.geofence_radius_meters or 0
        if distance > geofence_radius:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Clock-in location is {distance:.0f} m from the project site, "
                    f"exceeding the geofence radius of {geofence_radius} m."
                ),
            )

    now = datetime.now(timezone.utc)
    entry = TimeEntry(
        employee_id=employee.id,
        project_id=project.id,
        cost_code_id=payload.cost_code_id,
        clock_in=now,
        clock_out=None,
        latitude_in=payload.latitude_in,
        longitude_in=payload.longitude_in,
        latitude_out=None,
        longitude_out=None,
        notes=payload.notes,
        is_approved=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --- Clock out ---------------------------------------------------------------

@router.post("/clock-out", response_model=TimeEntryResponse)
def clock_out(
    payload: TimeEntryClockOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id
    employee = _get_employee_for_company(db, payload.employee_id, company_id)

    # Find open entry
    entry = db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == employee.id,
            TimeEntry.clock_out.is_(None),
        )
    ).scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open time entry found for this employee.",
        )

    now = datetime.now(timezone.utc)
    entry.clock_out = now
    entry.latitude_out = payload.latitude_out
    entry.longitude_out = payload.longitude_out
    if payload.notes is not None:
        entry.notes = payload.notes

    db.commit()
    db.refresh(entry)
    return entry


# --- List entries ------------------------------------------------------------

@router.get("/entries", response_model=list[TimeEntryResponse])
def list_entries(
    employee_id: Optional[int] = None,
    project_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_approved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    stmt = (
        select(TimeEntry)
        .join(Employee, TimeEntry.employee_id == Employee.id)
        .where(Employee.company_id == company_id)
    )

    if employee_id is not None:
        stmt = stmt.where(TimeEntry.employee_id == employee_id)
    if project_id is not None:
        stmt = stmt.where(TimeEntry.project_id == project_id)
    if date_from is not None:
        stmt = stmt.where(TimeEntry.clock_in >= date_from)
    if date_to is not None:
        stmt = stmt.where(TimeEntry.clock_in <= date_to)
    if is_approved is not None:
        stmt = stmt.where(TimeEntry.is_approved == is_approved)

    stmt = stmt.order_by(TimeEntry.clock_in.desc())
    entries = db.execute(stmt).scalars().all()
    return entries


# --- Single entry ------------------------------------------------------------

@router.get("/entries/{entry_id}", response_model=TimeEntryResponse)
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _get_time_entry_for_company(db, entry_id, current_user.company_id)


# --- Update entry ------------------------------------------------------------

@router.put("/entries/{entry_id}", response_model=TimeEntryResponse)
def update_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    entry = _get_time_entry_for_company(db, entry_id, current_user.company_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


# --- Approve entry -----------------------------------------------------------

@router.post("/approve/{entry_id}", response_model=TimeEntryResponse)
def approve_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers or admins can approve time entries.",
        )

    entry = _get_time_entry_for_company(db, entry_id, current_user.company_id)
    entry.is_approved = True
    db.commit()
    db.refresh(entry)
    return entry