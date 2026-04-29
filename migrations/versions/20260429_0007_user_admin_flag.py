"""add user admin flag

Revision ID: 20260429_0007
Revises: 20260429_0006
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0007"
down_revision: Union[str, None] = "20260429_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("users", "is_admin", server_default=sa.false())


def downgrade() -> None:
    op.drop_column("users", "is_admin")
