"""Dashboard router: company-wide stats and job costing breakdown."""

from datetime import datetime, timezone, date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Employee, Project, TimeEntry
from app.schemas import DashboardStats, JobCostingRow, JobCostingResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today_range_utc() -> tuple[datetime, datetime]:
    """Return (start_of_day_utc, end_of_day_utc) for today."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return today_start, today_end


# --- Company dashboard stats -------------------------------------------------

@router.get("", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    # active_crew: distinct employees clocked in right now (clock_out is None).
    active_crew_stmt = (
        select(func.count(func.distinct(TimeEntry.employee_id)))
        .join(Employee, TimeEntry.employee_id == Employee.id)
        .where(
            Employee.company_id == company_id,
            TimeEntry.clock_out.is_(None),
        )
    )
    active_crew = db.execute(active_crew_stmt).scalar() or 0

    today_start, today_end = _today_range_utc()

    # Fetch today's completed time entries with employee rates, compute in Python
    # (avoids PostgreSQL-specific func.extract("epoch", ...) that breaks SQLite).
    today_entries_stmt = (
        select(TimeEntry, Employee)
        .join(Employee, TimeEntry.employee_id == Employee.id)
        .where(
            Employee.company_id == company_id,
            TimeEntry.clock_out.is_not(None),
            TimeEntry.clock_in >= today_start,
            TimeEntry.clock_in < today_end,
        )
    )
    today_rows = db.execute(today_entries_stmt).all()

    hours_today = 0.0
    labor_cost_today = 0.0
    for entry, employee in today_rows:
        if entry.clock_in and entry.clock_out:
            seconds = (entry.clock_out - entry.clock_in).total_seconds()
            hours = seconds / 3600
            hours_today += hours
            rate = float(employee.hourly_rate or 0)
            labor_cost_today += hours * rate

    hours_today = round(hours_today, 2)
    labor_cost_today = round(labor_cost_today, 2)

    # projects_active: count of active projects.
    active_projects_stmt = select(func.count(Project.id)).where(
        Project.company_id == company_id,
        Project.status == "active",
    )
    projects_active = db.execute(active_projects_stmt).scalar() or 0

    return DashboardStats(
        active_crew=active_crew,
        hours_today=hours_today,
        projects_active=projects_active,
        labor_cost_today=labor_cost_today,
    )


# --- Job costing ---------------------------------------------------------------

@router.get("/job-costing", response_model=JobCostingResponse)
def get_job_costing(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    # Fetch all projects for the company.
    projects = db.execute(
        select(Project).where(Project.company_id == company_id)
    ).scalars().all()

    rows: List[JobCostingRow] = []

    for project in projects:
        # Get all completed time entries for this project (approved + pending).
        entries = db.execute(
            select(TimeEntry, Employee)
            .join(Employee, TimeEntry.employee_id == Employee.id)
            .where(
                TimeEntry.project_id == project.id,
                TimeEntry.clock_out.is_not(None),
            )
        ).all()

        actual_hours = 0.0
        actual_labor_cost = 0.0

        for entry, employee in entries:
            if entry.clock_in and entry.clock_out:
                seconds = (entry.clock_out - entry.clock_in).total_seconds()
                hours = seconds / 3600
                actual_hours += hours
                rate = float(employee.hourly_rate or 0)
                actual_labor_cost += hours * rate

        actual_hours = round(actual_hours, 2)
        actual_labor_cost = round(actual_labor_cost, 2)

        budget_hours = float(project.budget_hours or 0)
        budget_labor_cost = float(project.budget_labor_cost or 0)

        variance_hours = round(actual_hours - budget_hours, 2)
        variance_cost = round(actual_labor_cost - budget_labor_cost, 2)

        pct_budget_used = round(
            (actual_hours / budget_hours) * 100 if budget_hours > 0 else 0.0, 1
        )

        rows.append(
            JobCostingRow(
                project_id=project.id,
                project_name=project.name,
                budget_hours=budget_hours,
                actual_hours=actual_hours,
                budget_labor_cost=budget_labor_cost,
                actual_labor_cost=actual_labor_cost,
                variance_hours=variance_hours,
                variance_cost=variance_cost,
                pct_budget_used=pct_budget_used,
            )
        )

    return JobCostingResponse(projects=rows)