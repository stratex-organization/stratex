"""Pruebas del flujo de autenticación."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings

DEFAULT = settings.DEFAULT_PASSWORD


async def _register(client: AsyncClient, email: str = "ana@stratex.com") -> dict:
    resp = await client.post(
        "/v1/auth/register",
        json={"nombre": "Ana", "apellido": "López", "email": email},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post("/v1/auth/login", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_register_assigns_default_password(client: AsyncClient):
    data = await _register(client)
    assert data["default_password"] == DEFAULT
    assert data["user"]["must_change_password"] is True
    assert data["user"]["email"] == "ana@stratex.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_conflicts(client: AsyncClient):
    await _register(client)
    resp = await client.post(
        "/v1/auth/register",
        json={"nombre": "Otra", "apellido": "Ana", "email": "ana@stratex.com"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_with_default_password_flags_change(client: AsyncClient):
    await _register(client)
    resp = await _login(client, "ana@stratex.com", DEFAULT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["must_change_password"] is True


@pytest.mark.asyncio
async def test_login_wrong_password_is_401(client: AsyncClient):
    await _register(client)
    resp = await _login(client, "ana@stratex.com", "incorrecta")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_flow(client: AsyncClient):
    await _register(client)
    token = (await _login(client, "ana@stratex.com", DEFAULT)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/v1/auth/change-password",
        json={"current_password": DEFAULT, "new_password": "NuevaClave123"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["must_change_password"] is False

    # Con la nueva contraseña ya no se exige cambio.
    relog = await _login(client, "ana@stratex.com", "NuevaClave123")
    assert relog.status_code == 200
    assert relog.json()["user"]["must_change_password"] is False

    # La contraseña anterior ya no funciona.
    assert (await _login(client, "ana@stratex.com", DEFAULT)).status_code == 401


@pytest.mark.asyncio
async def test_change_password_rejects_default_and_short(client: AsyncClient):
    await _register(client)
    token = (await _login(client, "ana@stratex.com", DEFAULT)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Igual a la default → rechazada (422)
    same = await client.post(
        "/v1/auth/change-password",
        json={"current_password": DEFAULT, "new_password": DEFAULT},
        headers=headers,
    )
    assert same.status_code == 422

    # Muy corta → 422 por validación de Pydantic
    short = await client.post(
        "/v1/auth/change-password",
        json={"current_password": DEFAULT, "new_password": "abc1"},
        headers=headers,
    )
    assert short.status_code == 422


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    assert (await client.get("/v1/auth/me")).status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_returns_current_user(client: AsyncClient):
    await _register(client)
    token = (await _login(client, "ana@stratex.com", DEFAULT)).json()["access_token"]
    resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "ana@stratex.com"
