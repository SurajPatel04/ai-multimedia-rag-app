import pytest
from unittest.mock import patch
from app.models import User

async def test_get_me_success(authenticated_client):
    res = await authenticated_client.get("/api/v1/user/me")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "email" in data["data"]
    assert "first_name" in data["data"]
    assert "id" in data["data"]

async def test_get_me_unauthenticated(client):
    res = await client.get("/api/v1/user/me")
    assert res.status_code == 401

async def test_get_me_returns_correct_user(authenticated_client, registered_user):
    res = await authenticated_client.get("/api/v1/user/me")
    assert res.json()["data"]["email"] == registered_user["email"]



async def test_get_me_user_not_found(authenticated_client, registered_user):
    user = await User.find_one(User.email == registered_user["email"])
    if user:
        await user.delete()

    res = await authenticated_client.get("/api/v1/user/me")
    
    assert res.status_code == 404
    assert "User not found" in res.text


async def test_get_me_internal_server_error(authenticated_client):
    with patch("app.router.user.User.get", side_effect=Exception("Database failure!")):
        res = await authenticated_client.get("/api/v1/user/me")
        
        assert res.status_code == 500
        assert "Database failure!" in res.text