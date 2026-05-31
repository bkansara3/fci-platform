from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────
SECRET_KEY  = "use aws secrect manager"  
ALGORITHM   = "HS256"
TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ── Fake user store (replace with DB in production) ───────
FAKE_USERS = {
    "FCIAdmin": {
        "username": "FCIAdmin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
    },
    "FCIviewer": {
        "username": "FCIviewer",
        "hashed_password": pwd_context.hash("viewer123"),
        "role": "viewer",
    }
}

# ── Pydantic models ────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type:   str

class TokenData(BaseModel):
    username: Optional[str] = None
    role:     Optional[str] = None

class UserOut(BaseModel):
    username: str
    role:     str

# ── Core functions ─────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def authenticate_user(username: str, password: str):
    user = FAKE_USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire  = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ── FastAPI dependency — use this on protected routes ──────
def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role     = payload.get("role")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

def require_admin(current_user: TokenData = Depends(get_current_user)):
    """Use this on routes that only admins can access."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user