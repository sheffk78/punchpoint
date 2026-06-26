"""Employees router: CRUD + bulk import, scoped to the current user's company."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Employee, User
from app.schemas import (
    EmployeeBulkImportItem,
    EmployeeCreate,
    EmployeeResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _require_manager_or_admin(current_user: User) -> None:
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required.",
        )


def _get_company_employee_or_404(
    db: Session, employee_id: int, company_id: int
) -> Employee:
    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id, Employee.company_id == company_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )
    return employee


@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all employees for the current user's company."""
    return (
        db.query(Employee)
        .filter(Employee.company_id == current_user.company_id)
        .order_by(Employee.last_name, Employee.first_name)
        .all()
    )


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new employee for the current user's company (admin/manager only)."""
    _require_manager_or_admin(current_user)

    # Auto-generate employee_id if not provided
    if payload.employee_id:
        emp_id_str = payload.employee_id
    else:
        employee_count = (
            db.query(Employee)
            .filter(Employee.company_id == current_user.company_id)
            .count()
        )
        emp_id_str = f"EMP-{employee_count + 1:04d}"

    employee = Employee(
        company_id=current_user.company_id,
        employee_id=emp_id_str,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        hourly_rate=payload.hourly_rate,
        overtime_rate=payload.overtime_rate,
        is_active=True,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/bulk-import")
def bulk_import(
    payload: List[EmployeeBulkImportItem],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create multiple employees from a list. Returns count created."""
    _require_manager_or_admin(current_user)

    created_count = 0
    for item in payload:
        # Auto-generate employee_id if not provided
        if item.employee_id:
            emp_id_str = item.employee_id
        else:
            employee_count = (
                db.query(Employee)
                .filter(Employee.company_id == current_user.company_id)
                .count()
            )
            emp_id_str = f"EMP-{employee_count + created_count + 1:04d}"

        employee = Employee(
            company_id=current_user.company_id,
            employee_id=emp_id_str,
            first_name=item.first_name,
            last_name=item.last_name,
            phone=item.phone,
            hourly_rate=item.hourly_rate,
            overtime_rate=item.overtime_rate,
            is_active=True,
        )
        db.add(employee)
        created_count += 1

    db.commit()
    return {"created": created_count}


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single employee by ID."""
    return _get_company_employee_or_404(db, employee_id, current_user.company_id)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    payload: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing employee."""
    _require_manager_or_admin(current_user)

    employee = _get_company_employee_or_404(db, employee_id, current_user.company_id)
    employee.employee_id = payload.employee_id
    employee.first_name = payload.first_name
    employee.last_name = payload.last_name
    employee.phone = payload.phone
    employee.hourly_rate = payload.hourly_rate
    employee.overtime_rate = payload.overtime_rate
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
def deactivate_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an employee by setting is_active=False."""
    _require_manager_or_admin(current_user)

    employee = _get_company_employee_or_404(db, employee_id, current_user.company_id)
    employee.is_active = False
    db.commit()
    return {"detail": "Employee deactivated."}