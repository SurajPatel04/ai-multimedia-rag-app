import pytest
from app.models import User, RefreshToken
from unittest.mock import patch

from jose import jwt
from app.core.config import settings
import time

async def test_signup_success(client):
    email = "newuser@example.com"

    existing = await User.find_one({"email": email})
    if existing:
        await RefreshToken.find({"user_id": existing.id}).delete()
        await existing.delete()

    res = await client.post("/api/v1/auth/signUp", json={
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": "password123"
    })
    assert res.status_code == 201
    assert res.json()["success"] is True

    user = await User.find_one({"email": email})
    if user:
        await user.delete()

async def test_signup_duplicate_email(client, registered_user):
    res = await client.post("/api/v1/auth/signUp", json={
        "first_name": "Test",
        "email": registered_user["email"],
        "password": "password123"
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["message"] 


async def test_signup_missing_fields(client):
    res = await client.post("/api/v1/auth/signUp", json={
        "email": "incomplete@example.com"
    })
    assert res.status_code == 422

async def test_signin_success(client, registered_user):
    res = await client.post("/api/v1/auth/signIn", json=registered_user)
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies
    assert res.json()["email"] == registered_user["email"]

async def test_signin_wrong_password(client, registered_user):
    res = await client.post("/api/v1/auth/signIn", json={
        "email": registered_user["email"],
        "password": "wrongpassword"
    })
    assert res.status_code == 400
    assert "Invalid" in res.json()["message"]


async def test_signin_wrong_email(client):
    res = await client.post("/api/v1/auth/signIn", json={
        "email": "notexist@example.com",
        "password": "password123"
    })
    assert res.status_code == 400

async def test_signout_success(authenticated_client):
    res = await authenticated_client.post("/api/v1/auth/signOut")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "access_token" not in res.cookies
    assert "refresh_token" not in res.cookies

async def test_signout_without_token(client):
    res = await client.post("/api/v1/auth/signOut")
    assert res.status_code == 200

async def test_refresh_success(authenticated_client):
    res = await authenticated_client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies

async def test_refresh_no_token(client):
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 401
    assert "no refresh token" in res.json()["message"].lower()

async def test_refresh_revoked_token(authenticated_client):
    await authenticated_client.post("/api/v1/auth/signOut")
    res = await authenticated_client.post("/api/v1/auth/refresh")
    assert res.status_code == 401

async def test_refresh_token_not_in_db(client):
    payload = {"jti": "missing_jti", "sub": "some_user", "exp": time.time() + 3600}
    token = jwt.encode(payload, settings.REFRESH_TOKEN_SECRET, algorithm=settings.REFRESH_TOKEN_ALGORITHM)

    res = await client.post(
        "/api/v1/auth/refresh", 
        cookies={"refresh_token": token}
    )
    
    assert res.status_code == 401
    assert "token not found" in res.text.lower()


async def test_signup_internal_server_error(client):
    with patch("app.router.auth.hash", side_effect=Exception("Simulated hashing crash")):
        res = await client.post("/api/v1/auth/signUp", json={
            "first_name": "Crash",
            "last_name": "Test",
            "email": "crash@example.com",
            "password": "password123"
        })
        assert res.status_code == 500
        assert "Simulated hashing crash" in res.text


async def test_signin_internal_server_error(client):
    with patch("app.router.auth.User.find_one", side_effect=Exception("Simulated DB Crash")):
        res = await client.post("/api/v1/auth/signIn", json={
            "email": "crash@example.com",
            "password": "password123"
        })
        assert res.status_code == 500


async def test_signout_internal_server_error(client):
    with patch("app.router.auth.jwt.decode", side_effect=Exception("JWT Library Crash")):
        res = await client.post(
            "/api/v1/auth/signOut",
            cookies={"refresh_token": "dummy_token"}
        )
        
        assert res.status_code == 500