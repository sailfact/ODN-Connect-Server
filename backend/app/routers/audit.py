from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/admin", tags=["audit"])


class AuditOut(BaseModel):
    id: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/audit", response_model=list[AuditOut])
async def list_audit(
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    if action:
        q = q.where(AuditLog.action == action)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    result = await db.execute(q)
    return result.scalars().all()
