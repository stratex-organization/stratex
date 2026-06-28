"""Lógica de negocio de usuarios: alta, autenticación y cambio de contraseña."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, *, nombre: str, apellido: str, email: str) -> User:
    """Crea un usuario con la contraseña por defecto y la bandera de cambio obligatorio."""
    user = User(
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        email=email.lower().strip(),
        hashed_password=hash_password(settings.DEFAULT_PASSWORD),
        must_change_password=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User | None:
    """Devuelve el usuario si las credenciales son válidas y la cuenta está activa."""
    user = await get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def change_password(db: AsyncSession, *, user: User, new_password: str) -> User:
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    await db.commit()
    await db.refresh(user)
    return user
