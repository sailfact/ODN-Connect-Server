from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import pyotp

from app.db.session import get_db
from app.core.deps import require_admin, get_current_user
from app.core.security import hash_password
from app.models.user import User
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/admin", tags=["users"])


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    totp_enabled: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_extended(cls, u: User) -> "UserOut":
        return cls(id=u.id, email=u.email, role=u.role, is_active=u.is_active, totp_enabled=bool(u.totp_secret))


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


async def _audit(db: AsyncSession, actor_id: str, action: str, ip: str, target_id: str | None = None):
    log = AuditLog(actor_id=actor_id, action=action, target_type="user", target_id=target_id, ip_address=ip)
    db.add(log)
    await db.commit()


@router.get("/users", response_model=list[UserOut])
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return [UserOut.from_orm_extended(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = User(email=body.email, hashed_password=hash_password(body.password), role=body.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await _audit(db, admin.id, "user_created", request.client.host, user.id)
    return UserOut.from_orm_extended(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.delete(user)
    await db.commit()
    await _audit(db, admin.id, "user_deleted", request.client.host, user_id)


# ── Self-service: change password / TOTP ────────────────────────────────────

@router.post("/me/totp/setup")
async def setup_totp(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a new TOTP secret and return the provisioning URI."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(user.email, issuer_name="ODN VPN")
    # Don't persist until confirmed
    return {"secret": secret, "uri": uri}


@router.post("/me/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_totp(
    payload: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    secret = payload.get("secret")
    code = payload.get("code")
    if not secret or not code:
        raise HTTPException(status_code=400, detail="secret and code required")
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    user.totp_secret = secret
    await db.commit()
