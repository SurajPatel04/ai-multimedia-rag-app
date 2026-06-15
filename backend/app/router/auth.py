from fastapi import APIRouter, status, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt, JWTError
from app.models import User, RefreshToken
from app.schemas.auth import RegisterRequest, SignInRequest
from app.core.security import hash, verifyPassword
from app.services.auth_service import create_both_tokens
from app.core.config import settings
from app.core.limiter import limiter
from authlib.integrations.starlette_client import OAuth

# ---------------------------------------------------------------------------
# Google OAuth client setup
# ---------------------------------------------------------------------------
oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Local auth routes
# ---------------------------------------------------------------------------

@router.post("/signUp", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signUp(request: Request, body: RegisterRequest):
    existingUser = await User.find_one(User.email== body.email)
    if existingUser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    try:
        hashed_password = hash(body.password)
        user = User(
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            password=hashed_password,
            auth_provider="local"
        )
        await user.insert()
        return {
            "success": True,
            "message": "Account created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/signIn", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def signIn(request: Request, body: SignInRequest):
    try:
        user = await User.find_one(User.email== body.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")

        # Block password login for Google-only accounts
        if user.auth_provider == "google" and not user.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses Google sign-in. Please log in with Google."
            )

        if not verifyPassword(body.password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")
        
        tokens = await create_both_tokens(user.id)

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        is_secure = settings.ENV == "production"

        response = JSONResponse({
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "userId": str(user.id)
        })

        response.set_cookie(
            "access_token", 
            access_token, 
            httponly=True, 
            secure=is_secure, 
            samesite="lax", 
            max_age=settings.ACCESS_TOKEN_TTL, 
            path="/"
        )
        response.set_cookie(
            "refresh_token", 
            refresh_token, 
            httponly=True, 
            secure=is_secure, 
            samesite="lax", 
            max_age=settings.REFRESH_TOKEN_TTL, 
            path="/api/v1/auth"
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/signOut", status_code=status.HTTP_200_OK)
async def signOut(request: Request):
    try:
        refresh_token = request.cookies.get("refresh_token")

        if refresh_token:
            payload = jwt.decode(
                refresh_token, 
                settings.REFRESH_TOKEN_SECRET, 
                algorithms=[settings.REFRESH_TOKEN_ALGORITHM]
            )
            jti = payload.get("jti")
            
            if jti:
                token_data = await RefreshToken.find_one(RefreshToken.jti == jti)

                if token_data:
                    token_data.revoked = True
                    await token_data.save()

        response = JSONResponse({
            "success": True,
            "message": "Account signed out successfully"
        })
        response.delete_cookie(
            "access_token",
            path="/"
        )

        response.delete_cookie(
            "refresh_token",
            path="/api/v1/auth"
        )

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(request: Request):
    try:
        refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token"
            )

        payload = jwt.decode(
            refresh_token,
            settings.REFRESH_TOKEN_SECRET,
            algorithms=[
                settings.REFRESH_TOKEN_ALGORITHM
            ]
        )

        jti = payload.get("jti")
        user_id = payload.get("sub")

        if not jti or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        token_data = await RefreshToken.find_one(RefreshToken.jti == jti)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found"
            )

        if token_data.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked"
            )

        if not verifyPassword(
            refresh_token,
            token_data.token_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        token_data.revoked = True

        await token_data.save()

        tokens = await create_both_tokens( token_data.user_id)

        access_token = tokens["access_token"]
        new_refresh_token = tokens["refresh_token"]

        is_secure = (settings.ENV == "production")

        response = JSONResponse({
            "success": True,
            "message": "Tokens refreshed successfully"
        })

        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_TTL,
            path="/"
        )

        response.set_cookie(
            "refresh_token",
            new_refresh_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_TTL,
            path="/api/v1/auth"
        )

        return response

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    except HTTPException:
        raise

    except Exception as e:

        print(e)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong"
        )


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle the OAuth callback from Google.

    - Exchanges the authorization code for tokens.
    - Fetches the user's profile from Google.
    - Creates a new User document if this is the first login.
    - Issues access & refresh JWT cookies and redirects to the frontend.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google login failed: {str(e)}"
        )

    user_info = token.get("userinfo")
    if not user_info:
        # Fallback: fetch from the userinfo endpoint
        try:
            resp = await oauth.google.get("userinfo", token=token)
            user_info = resp.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google login failed: could not fetch user info"
            )

    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account does not have an email"
        )

    first_name = user_info.get("given_name", "")
    last_name = user_info.get("family_name", "")

    # Find or create user
    user = await User.find_one(User.email == email)

    if not user:
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=None,
            auth_provider="google",
        )
        await user.insert()

    # Issue JWT tokens
    tokens = await create_both_tokens(user.id)
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    is_secure = settings.ENV == "production"

    # Redirect to the frontend SPA after successful login
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/chat",
        status_code=302
    )

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_TTL,
        path="/"
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_TTL,
        path="/api/v1/auth"
    )

    return response