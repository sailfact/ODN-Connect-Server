"""add peer private_key and updated_at

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("peers", sa.Column("private_key", sa.String(64), nullable=True))
    op.add_column(
        "peers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Existing rows: treat created_at as the last modification time
    op.execute("UPDATE peers SET updated_at = created_at")


def downgrade() -> None:
    op.drop_column("peers", "updated_at")
    op.drop_column("peers", "private_key")
