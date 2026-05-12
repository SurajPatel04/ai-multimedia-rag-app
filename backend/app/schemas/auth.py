from typing import Optional
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    password: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str