import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.models.peer import Peer
from app.services.wg_manager import WgManager

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def server_status(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    wg = WgManager()
    peer_count_result = await db.execute(select(func.count()).select_from(Peer))
    total_peers = peer_count_result.scalar()

    enabled_result = await db.execute(select(func.count()).select_from(Peer).where(Peer.enabled == True))
    enabled_peers = enabled_result.scalar()

    handshakes = await wg.get_handshakes()

    return {
        "total_peers": total_peers,
        "enabled_peers": enabled_peers,
        "interface": wg.interface,
        "peer_handshakes": handshakes,
    }
