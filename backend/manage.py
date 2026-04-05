#!/usr/bin/env python
"""
Management commands for ODN Connect Server.

Usage:
  python manage.py init-wg      — Generate server WireGuard keypair
  python manage.py create-admin — Create an admin user interactively
"""
import asyncio
import subprocess
import sys
import os


def init_wg():
    """Generate server keypair and write to config volume."""
    config_dir = os.environ.get("WG_CONFIG_PATH", "/etc/wireguard/wg0.conf")
    config_dir = os.path.dirname(config_dir)
    priv_path = os.path.join(config_dir, "privatekey")
    pub_path = os.path.join(config_dir, "publickey")

    if os.path.exists(priv_path):
        print("Server keypair already exists — skipping.")
        return

    privkey = subprocess.check_output(["wg", "genkey"]).decode().strip()
    pubkey = subprocess.check_output(["wg", "pubkey"], input=privkey.encode()).decode().strip()

    os.makedirs(config_dir, exist_ok=True)
    with open(priv_path, "w") as f:
        f.write(privkey)
    os.chmod(priv_path, 0o600)

    with open(pub_path, "w") as f:
        f.write(pubkey)

    print(f"Server public key: {pubkey}")
    print(f"Keys written to {config_dir}")


async def _create_admin():
    import getpass
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    email = input("Admin email: ")
    password = getpass.getpass("Password: ")

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print("User already exists.")
            return
        user = User(email=email, hashed_password=hash_password(password), role="admin")
        db.add(user)
        await db.commit()
        print(f"Admin user {email} created. Set up TOTP before first login.")


def create_admin():
    asyncio.run(_create_admin())


COMMANDS = {
    "init-wg": init_wg,
    "create-admin": create_admin,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python manage.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
