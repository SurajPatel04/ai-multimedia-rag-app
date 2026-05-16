import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from app.models import User, RefreshToken
from app.main import app

@pytest_asyncio.fixture(scope="session")
async def initialized_app():
    async with LifespanManager(app, startup_timeout=30) as manager:
        yield manager.app


@pytest_asyncio.fixture
async def client(initialized_app):
    async with AsyncClient(
        transport=ASGITransport(app=initialized_app),
        base_url="http://test"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def registered_user(client):
    email = "test@example.com"

    existing = await User.find_one({"email": email})
    if existing:
        await RefreshToken.find({"user_id": existing.id}).delete()
        await existing.delete()

    await client.post("/api/v1/auth/signUp", json={
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": "password123"
    })

    yield {"email": email, "password": "password123"}

    user = await User.find_one({"email": email})
    if user:
        await RefreshToken.find({"user_id": user.id}).delete()
        await user.delete()

@pytest_asyncio.fixture
async def authenticated_client(client, registered_user):
    await client.post("/api/v1/auth/signIn", json=registered_user)
    return client