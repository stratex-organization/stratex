"""Schemas Pydantic para autenticación."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# La contraseña por defecto que se rechaza como contraseña nueva en el cambio.
from app.core.config import settings


class RegisterIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    apellido: str = Field(min_length=1, max_length=120)
    email: EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    apellido: str
    email: EmailStr
    must_change_password: bool


class RegisterOut(BaseModel):
    user: UserOut
    # Se devuelve para mostrarla en pantalla (no se envía por correo en esta iteración).
    default_password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    def validate_new_password(self) -> str | None:
        """Reglas de fortaleza; devuelve mensaje de error o None si es válida."""
        if self.new_password == self.current_password:
            return "La nueva contraseña debe ser distinta a la actual."
        if self.new_password == settings.DEFAULT_PASSWORD:
            return "La nueva contraseña no puede ser la contraseña por defecto."
        if not any(c.isalpha() for c in self.new_password) or not any(
            c.isdigit() for c in self.new_password
        ):
            return "La contraseña debe incluir letras y números."
        return None
