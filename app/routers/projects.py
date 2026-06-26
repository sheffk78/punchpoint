"""Projects router: CRUD for construction projects, scoped by company."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Project, User
from app.schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _require_manager_or_admin(current_user: User) -> None:
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required.",
        )


def _get_company_project_or_404(db: Session, project_id: int, company_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.company_id == company_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all projects for the company, optionally filtered by status."""
    query = db.query(Project).filter(Project.company_id == current_user.company_id)
    if status_filter:
        query = query.filter(Project.status == status_filter)
    return query.order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project (admin/manager only)."""
    _require_manager_or_admin(current_user)

    project = Project(
        company_id=current_user.company_id,
        name=payload.name,
        client_name=payload.client_name,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geofence_radius_meters=payload.geofence_radius_meters,
        budget_hours=payload.budget_hours,
        budget_labor_cost=payload.budget_labor_cost,
        status=payload.status if payload.status else "active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single project by ID."""
    return _get_company_project_or_404(db, project_id, current_user.company_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing project."""
    _require_manager_or_admin(current_user)

    project = _get_company_project_or_404(db, project_id, current_user.company_id)
    project.name = payload.name
    project.client_name = payload.client_name
    project.address = payload.address
    project.latitude = payload.latitude
    project.longitude = payload.longitude
    project.geofence_radius_meters = payload.geofence_radius_meters
    project.budget_hours = payload.budget_hours
    project.budget_labor_cost = payload.budget_labor_cost
    if payload.status:
        project.status = payload.status
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a project by setting status to 'completed'."""
    _require_manager_or_admin(current_user)

    project = _get_company_project_or_404(db, project_id, current_user.company_id)
    project.status = "completed"
    db.commit()
    return {"detail": "Project marked as completed."}