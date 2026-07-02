from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from auth.utils import hash_password
import re

router = APIRouter()

class User_SignUp(BaseModel): 
    name: str
    age: int
    email: EmailStr
    password:str = Field(..., min_length = 8, max_length = 32)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, value: str) -> str:

        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number.")
        
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one symbol.")
        return value

temp_Db = {}

@router.post("/signup")

def Create_User(Userdata: User_SignUp):
    
    if Userdata.email in temp_Db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{Userdata.email}' is already taken.")

    hashed_pass = hash_password(Userdata.password)

    temp_Db[Userdata.email] = {
        "name": Userdata.name,
        "age": Userdata.age,
        "email": Userdata.email,
        "password": hashed_pass  
    }
    
    return {
        "message": "User registered successfully!",
        "user_email": Userdata.email
    }
