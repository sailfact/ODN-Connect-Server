from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import pyotp

from app.db.session import get_db
from app.core.config import settings
from app.core.redis import get_redis
from app.core.ratelimit import rate_limit
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.models.audit import AuditLog
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.JWT_ACCESS_TTL


class RefreshRequest(BaseModel):
    refresh_token: str


async def _audit(db: AsyncSession, actor_id: str | None, action: str, ip: str, detail: dict | None = None):
    log = AuditLog(actor_id=actor_id, action=action, ip_address=ip, detail=detail)
    db.add(log)
    await db.commit()


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login", 5))])
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        await _audit(db, None, "login_failed", request.client.host, {"email": body.email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        # Same message as bad credentials — don't leak account state
        await _audit(db, user.id, "login_disabled_account", request.client.host)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # TOTP required for admins; optional for users (but validated if secret is set)
    if user.totp_secret:
        if not body.totp_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOTP code required")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(body.totp_code, valid_window=1):
            await _audit(db, user.id, "login_totp_failed", request.client.host)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")
    elif user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts must have TOTP enabled",
        )

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)

    # Store refresh token in Redis
    r = get_redis()
    await r.setex(f"refresh:{refresh}", settings.JWT_REFRESH_TTL, user.id)

    await _audit(db, user.id, "login_success", request.client.host)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit("refresh", 10))])
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    r = get_redis()
    stored = await r.get(f"refresh:{body.refresh_token}")
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Rotate
    await r.delete(f"refresh:{body.refresh_token}")

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id)
    await r.setex(f"refresh:{new_refresh}", settings.JWT_REFRESH_TTL, user.id)

    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, user: User = Depends(get_current_user)):
    await get_redis().delete(f"refresh:{body.refresh_token}")
