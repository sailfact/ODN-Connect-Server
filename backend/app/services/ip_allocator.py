import ipaddress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.peer import Peer


async def allocate_ip(db: AsyncSession, subnet: str) -> str:
    """
    Sequentially allocate the next free IP from the given subnet.
    Reserves .1 for the server gateway.
    """
    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts = list(network.hosts())

    result = await db.execute(select(Peer.assigned_ip))
    used = {row[0] for row in result.fetchall()}

    for host in hosts[1:]:  # skip .1 (server)
        ip_str = str(host)
        if ip_str not in used:
            return ip_str

    raise HTTPException(status_code=503, detail="IP address pool exhausted")
