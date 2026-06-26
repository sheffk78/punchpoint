"""Cost codes router: CRUD for cost codes, scoped by company."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CostCode, User
from app.schemas import CostCodeCreate, CostCodeResponse

router = APIRouter(prefix="/api/cost-codes", tags=["cost-codes"])


def _require_manager_or_admin(current_user: User) -> None:
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required.",
        )


def _get_company_cost_code_or_404(
    db: Session, cost_code_id: int, company_id: int
) -> CostCode:
    cost_code = (
        db.query(CostCode)
        .filter(CostCode.id == cost_code_id, CostCode.company_id == company_id)
        .first()
    )
    if not cost_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost code not found.",
        )
    return cost_code


@router.get("", response_model=List[CostCodeResponse])
def list_cost_codes(
    active_only: bool = Query(False, description="Filter to only active cost codes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all cost codes for the company, optionally filtered to active only."""
    query = db.query(CostCode).filter(CostCode.company_id == current_user.company_id)
    if active_only:
        query = query.filter(CostCode.is_active == True)  # noqa: E712
    return query.order_by(CostCode.code).all()


@router.post("", response_model=CostCodeResponse, status_code=status.HTTP_201_CREATED)
def create_cost_code(
    payload: CostCodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new cost code (admin/manager only)."""
    _require_manager_or_admin(current_user)

    cost_code = CostCode(
        company_id=current_user.company_id,
        code=payload.code,
        description=payload.description,
        is_active=True,
    )
    db.add(cost_code)
    db.commit()
    db.refresh(cost_code)
    return cost_code


@router.put("/{cost_code_id}", response_model=CostCodeResponse)
def update_cost_code(
    cost_code_id: int,
    payload: CostCodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing cost code."""
    _require_manager_or_admin(current_user)

    cost_code = _get_company_cost_code_or_404(db, cost_code_id, current_user.company_id)
    cost_code.code = payload.code
    cost_code.description = payload.description
    db.commit()
    db.refresh(cost_code)
    return cost_code


@router.delete("/{cost_code_id}", status_code=status.HTTP_200_OK)
def deactivate_cost_code(
    cost_code_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a cost code by setting is_active=False."""
    _require_manager_or_admin(current_user)

    cost_code = _get_company_cost_code_or_404(db, cost_code_id, current_user.company_id)
    cost_code.is_active = False
    db.commit()
    return {"detail": "Cost code deactivated."}