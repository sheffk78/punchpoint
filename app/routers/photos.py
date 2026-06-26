"""Photos router: upload and list photos for projects."""

import os
import uuid
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Employee, Project, TimeEntry, Photo
from app.schemas import PhotoResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/photos", tags=["photos"])

# Directory where uploaded photos are stored.
PHOTOS_DIR = Path("photos")


@router.post("/upload", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    employee_id: int = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    timestamp: datetime = Form(...),
    time_entry_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    # Validate project belongs to company.
    project = db.execute(
        select(Project).where(Project.id == project_id, Project.company_id == company_id)
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your company.",
        )

    # Validate employee belongs to company.
    employee = db.execute(
        select(Employee).where(
            Employee.id == employee_id, Employee.company_id == company_id
        )
    ).scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company.",
        )

    # Validate time entry if provided.
    if time_entry_id is not None:
        entry = db.execute(
            select(TimeEntry)
            .join(Employee, TimeEntry.employee_id == Employee.id)
            .where(TimeEntry.id == time_entry_id, Employee.company_id == company_id)
        ).scalar_one_or_none()
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found in your company.",
            )

    # Ensure photos directory exists.
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename preserving the original extension.
    original_ext = Path(file.filename).suffix if file.filename else ""
    stored_filename = f"{uuid.uuid4().hex}{original_ext}"
    file_path = PHOTOS_DIR / stored_filename

    # Save file to disk.
    content = await file.read()
    file_path.write_bytes(content)

    # Create the Photo record.
    photo = Photo(
        project_id=project.id,
        employee_id=employee.id,
        time_entry_id=time_entry_id,
        filename=stored_filename,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        timestamp=timestamp,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("", response_model=list[PhotoResponse])
def list_photos(
    project_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    company_id = current_user.company_id

    stmt = (
        select(Photo)
        .join(Project, Photo.project_id == Project.id)
        .where(Project.company_id == company_id)
    )

    if project_id is not None:
        stmt = stmt.where(Photo.project_id == project_id)
    if date_from is not None:
        stmt = stmt.where(Photo.timestamp >= date_from)
    if date_to is not None:
        stmt = stmt.where(Photo.timestamp <= date_to)

    stmt = stmt.order_by(Photo.timestamp.desc())
    photos = db.execute(stmt).scalars().all()
    return photos