import logging
from fastapi import Request, HTTPException, status
from jose import JWTError, jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

def verify_access_token(token: str, credential_exception):
    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET,
            algorithms=[settings.ACCESS_TOKEN_ALGORITHM]
        )

        user_id: str = payload.get("sub")

        if user_id is None:
            raise credential_exception

        return user_id

    except JWTError as e:
        logging.warning("verify_access_token failed: %s", repr(e))
        raise credential_exception

def get_current_user(request: Request):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate access token",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    cookie_token = request.cookies.get("access_token")

    if not cookie_token:
        logger.warning("access_token cookie not found")
        raise credential_exception

    try:
        return verify_access_token(cookie_token,credential_exception)

    except JWTError as e:
        logger.warning("Token verification failed: %s", repr(e))

        raise credential_exception