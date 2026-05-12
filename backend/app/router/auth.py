from fastapi import APIRouter, status, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from app.models import User, RefreshToken
from schemas.auth import RegisterRequest, SignInRequest
from app.core.security import hash, verifyPassword
from services import create_both_tokens
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signUp", status_code=status.HTTP_201_CREATED)
async def signUp(request: RegisterRequest):
    existingUser = await User.find_one(User.email== request.email)
    if existingUser:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    try:
        hashed_password = hash(request.password)
        user = User(
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            password=hashed_password
        )
        await user.insert()
        return {
            "success": True,
            "message": "Account created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/signIn", status_code=status.HTTP_200_OK)
async def signIn(request: SignInRequest):
    try:
        user = await User.find_one(User.email== request.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not exist")
        
        if not verifyPassword(request.password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password")
        
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

        response = JSONResponse({"message": "Tokens refreshed successfully"})

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