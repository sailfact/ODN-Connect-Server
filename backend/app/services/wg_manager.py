import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings


class WgManager:
    """
    Manages WireGuard configuration and live peer sync.

    Writes peer stanzas atomically (write → rename) and calls
    `wg syncconf` for hot-reload without tearing down the tunnel.
    """

    def __init__(self):
        self.interface = settings.WG_INTERFACE
        self.config_path = settings.WG_CONFIG_PATH

    # ── Key generation ────────────────────────────────────────────────────────

    async def generate_peer_keys(self, supplied_public_key: Optional[str] = None) -> tuple[str, str]:
        """
        Returns (public_key, preshared_key).
        If the client supplied its own public key (self-service flow), use it.
        Otherwise generate a new keypair — the private key is stored nowhere.
        """
        if supplied_public_key:
            pub_key = supplied_public_key.strip()
        else:
            proc = await asyncio.create_subprocess_exec(
                "wg", "genkey",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            privkey = stdout.decode().strip()

            proc = await asyncio.create_subprocess_exec(
                "wg", "pubkey",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate(input=privkey.encode())
            pub_key = stdout.decode().strip()

        # Always generate a preshared key
        proc = await asyncio.create_subprocess_exec(
            "wg", "genpsk",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        psk = stdout.decode().strip()

        return pub_key, psk

    async def get_server_public_key(self) -> str:
        """Read the server's public key from the wg interface or config file."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "wg", "show", self.interface, "public-key",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
        except FileNotFoundError:
            pass

        # Fallback: read from config
        pub_key_path = os.path.join(os.path.dirname(self.config_path), "publickey")
        if os.path.exists(pub_key_path):
            with open(pub_key_path) as f:
                return f.read().strip()

        return "UNKNOWN"

    # ── Config sync ───────────────────────────────────────────────────────────

    async def sync_peer(self, peer) -> None:
        """Rewrite the full wg0.conf and apply it live."""
        await self._rewrite_config()

    async def remove_peer(self, public_key: str) -> None:
        """Remove a peer by public key using `wg set`."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "wg", "set", self.interface, "peer", public_key, "remove",
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except FileNotFoundError:
            pass  # wg not available in this environment
        await self._rewrite_config()

    async def _rewrite_config(self) -> None:
        """
        Rebuild wg0.conf from DB and atomically replace the file,
        then call wg syncconf for hot-reload.

        NOTE: This is called after the DB session has already committed,
        so we import session here to avoid circular dep issues.
        """
        from app.db.session import AsyncSessionLocal
        from app.models.peer import Peer
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Peer).where(Peer.enabled == True))
            peers = result.scalars().all()

        lines = [self._server_header()]
        for p in peers:
            lines.append(self._peer_stanza(p))

        config_content = "\n".join(lines)

        config_dir = os.path.dirname(self.config_path)
        if not os.path.isdir(config_dir):
            return  # running outside docker, skip

        tmp_fd, tmp_path = tempfile.mkstemp(dir=config_dir)
        try:
            with os.fdopen(tmp_fd, "w") as f:
                f.write(config_content)
            os.chmod(tmp_path, 0o600)
            shutil.move(tmp_path, self.config_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return

        await self._syncconf()

    async def _syncconf(self) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "wg", "syncconf", self.interface, self.config_path,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except FileNotFoundError:
            pass

    def _server_header(self) -> str:
        return f"""[Interface]
# Managed by ODN-Connect-Server — do not edit manually
PrivateKey = ${{WG_PRIVATE_KEY}}
Address = {settings.WG_SUBNET.replace("0/24", "1/24")}
ListenPort = {settings.WG_PORT}
DNS = {settings.WG_DNS}
"""

    def _peer_stanza(self, peer) -> str:
        lines = [
            f"[Peer]",
            f"# {peer.name} ({peer.id})",
            f"PublicKey = {peer.public_key}",
            f"AllowedIPs = {peer.assigned_ip}/32",
        ]
        if peer.preshared_key:
            lines.append(f"PresharedKey = {peer.preshared_key}")
        return "\n".join(lines) + "\n"

    # ── Client config rendering ───────────────────────────────────────────────

    async def render_client_config(self, peer) -> str:
        server_pubkey = await self.get_server_public_key()
        lines = [
            "[Interface]",
            f"# {peer.name}",
            f"Address = {peer.assigned_ip}/32",
            f"DNS = {peer.dns or settings.WG_DNS}",
            "",
            "[Peer]",
            f"PublicKey = {server_pubkey}",
            f"Endpoint = {settings.WG_SERVER_PUBLIC_IP}:{settings.WG_PORT}",
            f"AllowedIPs = {peer.allowed_ips}",
            "PersistentKeepalive = 25",
        ]
        if peer.preshared_key:
            lines.insert(lines.index("[Peer]") + 1, f"PresharedKey = {peer.preshared_key}")
        return "\n".join(lines) + "\n"

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_handshakes(self) -> dict:
        try:
            proc = await asyncio.create_subprocess_exec(
                "wg", "show", self.interface, "latest-handshakes",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            handshakes = {}
            for line in stdout.decode().splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    pubkey, ts = parts
                    if int(ts) == 0:  # wg reports 0 for "never"
                        continue
                    handshakes[pubkey] = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            return handshakes
        except (FileNotFoundError, ValueError):
            return {}

    async def persist_handshakes(self, db) -> dict:
        """Read live handshakes and write them back to peers.last_handshake.

        Returns {public_key: datetime}. Commits only if something changed.
        """
        from sqlalchemy import select
        from app.models.peer import Peer

        handshakes = await self.get_handshakes()
        if not handshakes:
            return {}

        result = await db.execute(select(Peer).where(Peer.public_key.in_(handshakes.keys())))
        dirty = False
        for peer in result.scalars().all():
            ts = handshakes[peer.public_key]
            if peer.last_handshake != ts:
                peer.last_handshake = ts
                dirty = True
        if dirty:
            await db.commit()
        return handshakes
