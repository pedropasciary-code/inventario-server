"""add asset network interfaces

Revision ID: 20260429_0004
Revises: 20260429_0003
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0004"
down_revision: Union[str, None] = "20260429_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("network_interfaces", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "network_interfaces")
