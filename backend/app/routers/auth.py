from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from app.auth import authenticate_user, create_access_token, Token, get_current_user, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({
        "sub":  user["username"],
        "role": user["role"],
    })
    return Token(access_token=token, token_type="bearer")

@router.get("/me", response_model=UserOut)
def get_me(current_user = Depends(get_current_user)):
    return UserOut(username=current_user.username, role=current_user.role)