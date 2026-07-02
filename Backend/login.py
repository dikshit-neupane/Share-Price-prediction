from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from auth.utils import verify_password, create_token
from signup import temp_Db

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class User_Login(BaseModel):
    email : EmailStr
    password : str

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        email = verify_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = temp_Db.get(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/login")

def Login_user(login: User_Login):
    if login.email not in temp_Db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid Email or Password" 
            )
    
    storedUser = temp_Db[login.email]

    if not verify_password(login.password, storedUser["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Email or password"
        )
    
@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return {
        "name": current_user["name"],
        "email": current_user["email"],
        "age": current_user["age"]
    }
