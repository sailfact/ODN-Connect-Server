import ipaddress
import zlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import HTTPException

from app.models.peer import Peer


async def allocate_ip(db: AsyncSession, subnet: str) -> str:
    """
    Sequentially allocate the next free IP from the given subnet.
    Reserves .1 for the server gateway.

    Serialized with a Postgres transaction-scoped advisory lock so two
    concurrent peer creations cannot read the same free IP. The lock is
    released automatically at commit/rollback, and the unique constraint on
    peers.assigned_ip remains as a backstop.
    """
    if db.bind.dialect.name == "postgresql":
        lock_key = zlib.crc32(f"ip_alloc:{subnet}".encode())
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts = list(network.hosts())

    result = await db.execute(select(Peer.assigned_ip))
    used = {row[0] for row in result.fetchall()}

    for host in hosts[1:]:  # skip .1 (server)
        ip_str = str(host)
        if ip_str not in used:
            return ip_str

    raise HTTPException(status_code=503, detail="IP address pool exhausted")
