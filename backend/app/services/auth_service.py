from jose import jwt
from datetime import datetime, timedelta, timezone
from beanie import PydanticObjectId
from uuid import uuid4

from app.core.config import settings
from app.core.security import hash
from app.models import RefreshToken



ACCESS_TOKEN_SECRET_KEY = settings.ACCESS_TOKEN_SECRET
REFRESH_TOKEN_SECRET_KEY = settings.REFRESH_TOKEN_SECRET

ACCESS_TOKEN_ALGORITHM = settings.ACCESS_TOKEN_ALGORITHM
REFRESH_TOKEN_ALGORITHM = settings.REFRESH_TOKEN_ALGORITHM


ACCESS_TOKEN_TTL = settings.ACCESS_TOKEN_TTL
REFRESH_TOKEN_TTL = settings.REFRESH_TOKEN_TTL

async def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_TTL))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, ACCESS_TOKEN_SECRET_KEY, algorithm=ACCESS_TOKEN_ALGORITHM)
    return encoded_jwt

async def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=int(REFRESH_TOKEN_TTL))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_TOKEN_SECRET_KEY, algorithm=REFRESH_TOKEN_ALGORITHM)
    return encoded_jwt

async def create_both_tokens(user_id: PydanticObjectId):

    access_token = await create_access_token({"sub": str(user_id)})

    jti = str(uuid4())

    refresh_token = await create_refresh_token({"sub": str(user_id), "jti": jti})

    hashed_refresh_token = hash(refresh_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=int(REFRESH_TOKEN_TTL))

    refresh_token_doc = RefreshToken(
        user_id=user_id,
        jti=jti,
        token_hash=hashed_refresh_token,
        expires_at=expires_at,
        revoked=False
    )

    await refresh_token_doc.insert()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }