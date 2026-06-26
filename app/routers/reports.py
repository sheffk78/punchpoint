"""Daily reports router: CRUD for project daily reports."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Project, DailyReport
from app.schemas import DailyReportCreate, DailyReportResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/daily-reports", tags=["daily-reports"])


def _get_report_for_company(
    db: Session, report_id: int, company_id: int
) -> DailyReport:
    """Return a DailyReport that belongs to *company_id* via project, or raise 404."""
    stmt = (
        select(DailyReport)
        .join(Project, DailyReport.project_id == Project.id)
        .where(DailyReport.id == report_id, Project.company_id == company_id)
    )
    report = db.execute(stmt).scalar_one_or_none()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily report not found in your company.",
        )
    return report


# --- List reports -------------------------------------------------------------

@router.get("", response_model=list[DailyReportResponse])
def list_reports(
    project_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    stmt = (
        select(DailyReport)
        .join(Project, DailyReport.project_id == Project.id)
        .where(Project.company_id == company_id)
    )

    if project_id is not None:
        stmt = stmt.where(DailyReport.project_id == project_id)
    if date_from is not None:
        stmt = stmt.where(DailyReport.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyReport.date <= date_to)

    stmt = stmt.order_by(DailyReport.date.desc())
    reports = db.execute(stmt).scalars().all()
    return reports


# --- Create report ------------------------------------------------------------

@router.post("", response_model=DailyReportResponse, status_code=201)
def create_report(
    payload: DailyReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    # Validate project belongs to company.
    project = db.execute(
        select(Project).where(Project.id == payload.project_id, Project.company_id == company_id)
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your company.",
        )

    report = DailyReport(
        project_id=project.id,
        date=payload.date,
        weather=payload.weather,
        crew_summary=payload.crew_summary,
        hours_total=payload.hours_total,
        injuries_reported=payload.injuries_reported,
        notes=payload.notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --- Get single report --------------------------------------------------------

@router.get("/{report_id}", response_model=DailyReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _get_report_for_company(db, report_id, current_user.company_id)


# --- Update report -------------------------------------------------------------

@router.put("/{report_id}", response_model=DailyReportResponse)
def update_report(
    report_id: int,
    payload: DailyReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = _get_report_for_company(db, report_id, current_user.company_id)

    # If project_id is being changed, verify the new project belongs to the company.
    if payload.project_id != report.project_id:
        project = db.execute(
            select(Project).where(
                Project.id == payload.project_id, Project.company_id == current_user.company_id
            )
        ).scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in your company.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report