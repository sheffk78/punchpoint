"""Authentication router: register, login, and current-user endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.database import get_db
from app.models import Company, User
from app.schemas import AuthLogin, AuthRegister, Token, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegister, db: Session = Depends(get_db)):
    """Register a new company and an admin user; return access token + user info."""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    company = Company(name=payload.company_name)
    db.add(company)
    db.commit()
    db.refresh(company)

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="admin",
        company_id=company.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": str(user.id), "company_id": str(company.id)}, expires_delta=expires_delta
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user, from_attributes=True).model_dump(),
    }


@router.post("/login", response_model=Token)
def login(payload: AuthLogin, db: Session = Depends(get_db)):
    """Authenticate by email + password and return a JWT bearer token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": str(user.id), "company_id": str(user.company_id)},
        expires_delta=expires_delta,
    )
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user