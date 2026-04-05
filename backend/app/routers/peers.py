from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.models.peer import Peer
from app.models.audit import AuditLog
from app.services.wg_manager import WgManager
from app.services.ip_allocator import allocate_ip
from app.core.config import settings

router = APIRouter(tags=["peers"])


class PeerOut(BaseModel):
    id: str
    user_id: str
    name: str
    public_key: str
    allowed_ips: str
    assigned_ip: str
    dns: str | None
    enabled: bool
    last_handshake: datetime | None
    client_label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PeerCreate(BaseModel):
    name: str
    public_key: str | None = None    # client supplies when self-service
    allowed_ips: str = "0.0.0.0/0"
    dns: str | None = None
    client_label: str | None = None


class PeerUpdate(BaseModel):
    enabled: bool | None = None
    name: str | None = None
    allowed_ips: str | None = None


async def _audit(db: AsyncSession, actor_id: str, action: str, ip: str, target_id: str | None = None, detail: dict | None = None):
    log = AuditLog(actor_id=actor_id, action=action, target_type="peer", target_id=target_id, ip_address=ip, detail=detail)
    db.add(log)
    await db.commit()


# ── Admin: all peers ─────────────────────────────────────────────────────────

@router.get("/api/peers", response_model=list[PeerOut])
async def list_peers(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Peer))
    return result.scalars().all()


@router.post("/api/peers", response_model=PeerOut, status_code=status.HTTP_201_CREATED)
async def create_peer(
    body: PeerCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    wg = WgManager()
    pub_key, psk = await wg.generate_peer_keys(body.public_key)
    assigned_ip = await allocate_ip(db, settings.WG_SUBNET)

    peer = Peer(
        user_id=admin.id,
        name=body.name,
        public_key=pub_key,
        preshared_key=psk,
        allowed_ips=body.allowed_ips,
        assigned_ip=assigned_ip,
        dns=body.dns or settings.WG_DNS,
        client_label=body.client_label,
    )
    db.add(peer)
    await db.flush()
    await wg.sync_peer(peer)
    await db.commit()
    await db.refresh(peer)
    await _audit(db, admin.id, "peer_created", request.client.host, peer.id, {"name": peer.name})
    return peer


@router.delete("/api/peers/{peer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_peer(
    peer_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Peer).where(Peer.id == peer_id))
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    wg = WgManager()
    await wg.remove_peer(peer.public_key)
    await db.delete(peer)
    await db.commit()
    await _audit(db, admin.id, "peer_deleted", request.client.host, peer_id)


@router.patch("/api/peers/{peer_id}", response_model=PeerOut)
async def update_peer(
    peer_id: str,
    body: PeerUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Peer).where(Peer.id == peer_id))
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    if body.enabled is not None:
        peer.enabled = body.enabled
    if body.name is not None:
        peer.name = body.name
    if body.allowed_ips is not None:
        peer.allowed_ips = body.allowed_ips

    wg = WgManager()
    await wg.sync_peer(peer)
    await db.commit()
    await db.refresh(peer)
    await _audit(db, admin.id, "peer_updated", request.client.host, peer_id, body.model_dump(exclude_none=True))
    return peer


# ── User: own peers ───────────────────────────────────────────────────────────

@router.get("/api/me/peers", response_model=list[PeerOut])
async def list_my_peers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Peer).where(Peer.user_id == user.id))
    return result.scalars().all()


@router.get("/api/me/peers/{peer_id}/config")
async def get_peer_config(
    peer_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Peer).where(Peer.id == peer_id, Peer.user_id == user.id))
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    wg = WgManager()
    config = await wg.render_client_config(peer)

    last_modified = peer.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return PlainTextResponse(
        content=config,
        headers={
            "Content-Type": "text/plain",
            "Last-Modified": last_modified,
            "Content-Disposition": f'attachment; filename="{peer.name}.conf"',
        },
    )


@router.post("/api/me/peers", response_model=PeerOut, status_code=status.HTTP_201_CREATED)
async def create_my_peer(
    body: PeerCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ODN_CLIENT_SELF_SERVICE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-service peer creation is disabled")

    wg = WgManager()
    pub_key, psk = await wg.generate_peer_keys(body.public_key)
    assigned_ip = await allocate_ip(db, settings.WG_SUBNET)

    peer = Peer(
        user_id=user.id,
        name=body.name,
        public_key=pub_key,
        preshared_key=psk,
        allowed_ips=body.allowed_ips,
        assigned_ip=assigned_ip,
        dns=body.dns or settings.WG_DNS,
        client_label=body.client_label,
    )
    db.add(peer)
    await db.flush()
    await wg.sync_peer(peer)
    await db.commit()
    await db.refresh(peer)
    await _audit(db, user.id, "self_service_peer_created", request.client.host, peer.id, {"name": peer.name, "label": body.client_label})
    return peer


@router.delete("/api/me/peers/{peer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_peer(
    peer_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Peer).where(Peer.id == peer_id, Peer.user_id == user.id))
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    wg = WgManager()
    await wg.remove_peer(peer.public_key)
    await db.delete(peer)
    await db.commit()
    await _audit(db, user.id, "peer_deleted", request.client.host, peer_id)
