"""Endpoints de autenticación: register, login, me, change-password."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordIn,
    LoginIn,
    RegisterIn,
    RegisterOut,
    TokenOut,
    UserOut,
)
from app.services import user_service
from app.services.email import send_password_changed_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)) -> RegisterOut:
    """Alta controlada de usuario. Asigna la contraseña por defecto (cambio obligatorio)."""
    existing = await user_service.get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo electrónico.",
        )
    user = await user_service.create_user(
        db, nombre=payload.nombre, apellido=payload.apellido, email=payload.email
    )
    return RegisterOut(user=UserOut.model_validate(user), default_password=settings.DEFAULT_PASSWORD)


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    """Valida credenciales y emite un JWT. Mensaje genérico para no filtrar información."""
    user = await user_service.authenticate(db, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"must_change_password": user.must_change_password},
    )
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/change-password", response_model=UserOut)
async def change_password(
    payload: ChangePasswordIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Cambia la contraseña del usuario autenticado (usado en el primer login obligatorio)."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    error = payload.validate_new_password()
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    user = await user_service.change_password(db, user=current_user, new_password=payload.new_password)
    await send_password_changed_email(to_email=user.email, nombre=user.nombre)
    return UserOut.model_validate(user)
