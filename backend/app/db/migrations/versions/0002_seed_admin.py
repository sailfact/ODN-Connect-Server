"""seed default admin user

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05 00:00:01.000000

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def upgrade() -> None:
    users_table = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(users_table, [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@example.com",
            "hashed_password": pwd_context.hash("changeme"),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ])


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email = 'admin@example.com'")
