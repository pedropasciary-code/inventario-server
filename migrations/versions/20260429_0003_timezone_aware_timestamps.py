"""use timezone-aware timestamps

Revision ID: 20260429_0003
Revises: 20260429_0002
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0003"
down_revision: Union[str, None] = "20260429_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "assets",
        "ultimo_boot",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="ultimo_boot AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
    op.alter_column(
        "assets",
        "ultima_comunicacao",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="ultima_comunicacao AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
        existing_nullable=False,
    )
    op.alter_column(
        "assets",
        "ultima_comunicacao",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="ultima_comunicacao AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
    op.alter_column(
        "assets",
        "ultimo_boot",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="ultimo_boot AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
