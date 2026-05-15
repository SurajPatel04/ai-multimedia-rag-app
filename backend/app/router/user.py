from fastapi import APIRouter, status, HTTPException, Depends
from app.models import User
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/user",
    tags=["user"]
)


@router.get("/me",status_code=status.HTTP_200_OK)
async def get_me(current_user: str = Depends(get_current_user)):
    try:
        user = await User.get(current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        data = {
            'id': str(user.id),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'createdAt': user.created_at,
            'updatedAt': user.updated_at
        }
        return {
            "success": True,
            "message": "User fetched successfully",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )