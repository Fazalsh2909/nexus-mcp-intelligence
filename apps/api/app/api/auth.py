from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import jwt
import bcrypt
import re
from typing import Optional

from app.db.session import get_db
from app.models.models import User, Organization
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.config import settings

router = APIRouter()

PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def _validate_password(password: str) -> Optional[str]:
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if not PASSWORD_PATTERN.match(password):
        return "Password must contain at least one uppercase letter, one lowercase letter, and one number"
    return None


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/register", response_model=UserResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    password_error = _validate_password(data.password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    email = data.email.strip().lower()
    existing = await db.execute(select(User).where(func.lower(User.email) == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    org = Organization(
        name=f"{data.name}'s Organization", slug=data.email.split("@")[0]
    )
    db.add(org)
    await db.flush()

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())
    user = User(
        email=email,
        name=data.name,
        hashed_password=hashed.decode(),
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    email = data.email.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalar_one_or_none()
    if (
        not user
        or not user.hashed_password
        or not bcrypt.checkpw(data.password.encode(), user.hashed_password.encode())
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": str(user.id),
            "org_id": str(user.organization_id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    return user
