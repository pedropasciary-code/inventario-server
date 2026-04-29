"""add asset checkin history

Revision ID: 20260429_0005
Revises: 20260429_0004
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0005"
down_revision: Union[str, None] = "20260429_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("usuario", sa.String(), nullable=True),
        sa.Column("serial", sa.String(), nullable=True),
        sa.Column("mac_address", sa.String(), nullable=True),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("agent_version", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_checkins_id", "asset_checkins", ["id"])
    op.create_index("ix_asset_checkins_asset_id", "asset_checkins", ["asset_id"])
    op.create_index("ix_asset_checkins_serial", "asset_checkins", ["serial"])
    op.create_index("ix_asset_checkins_mac_address", "asset_checkins", ["mac_address"])
    op.create_index("ix_asset_checkins_created_at", "asset_checkins", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_asset_checkins_created_at", table_name="asset_checkins")
    op.drop_index("ix_asset_checkins_mac_address", table_name="asset_checkins")
    op.drop_index("ix_asset_checkins_serial", table_name="asset_checkins")
    op.drop_index("ix_asset_checkins_asset_id", table_name="asset_checkins")
    op.drop_index("ix_asset_checkins_id", table_name="asset_checkins")
    op.drop_table("asset_checkins")
