import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.db.mongo import users_collection
from app.db.schemas import UserCreate, UserLogin, Token

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger("solsight.auth")

SECRET_KEY = os.getenv("JWT_SECRET", "")
if not SECRET_KEY:
    SECRET_KEY = "solsight-dev-secret-change-me"
    log.warning("JWT_SECRET is not set; using the development default")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 24))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# passlib 1.7.4 is unmaintained and crashes against bcrypt >= 4.1 on its own
# self-test, so hash with bcrypt directly. bcrypt only looks at the first
# 72 bytes; UserCreate rejects anything longer so nothing is silently cut.
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await users_collection.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    email = payload.email.lower()
    existing = await users_collection.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "name": payload.name.strip(),
        "email": email,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow(),
    }
    await users_collection.insert_one(user_doc)
    token = create_access_token({"sub": email})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(payload: UserLogin):
    email = payload.email.lower()
    user = await users_collection.find_one({"email": email})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": email})
    return Token(access_token=token)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"name": current_user["name"], "email": current_user["email"]}
