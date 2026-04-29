"""initial schema and indexes

Revision ID: 20260429_0001
Revises:
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def create_index_if_missing(index_name: str, table_name: str, columns: list[str], unique: bool = False):
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def drop_index_if_exists(index_name: str, table_name: str):
    if table_exists(table_name) and index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    if not table_exists("assets"):
        op.create_table(
            "assets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("hostname", sa.String(), nullable=True),
            sa.Column("usuario", sa.String(), nullable=True),
            sa.Column("cpu", sa.String(), nullable=True),
            sa.Column("ram", sa.String(), nullable=True),
            sa.Column("sistema", sa.String(), nullable=True),
            sa.Column("ip", sa.String(), nullable=True),
            sa.Column("serial", sa.String(), nullable=True),
            sa.Column("fabricante", sa.String(), nullable=True),
            sa.Column("modelo", sa.String(), nullable=True),
            sa.Column("motherboard", sa.String(), nullable=True),
            sa.Column("bios_version", sa.String(), nullable=True),
            sa.Column("arquitetura", sa.String(), nullable=True),
            sa.Column("versao_windows", sa.String(), nullable=True),
            sa.Column("mac_address", sa.String(), nullable=True),
            sa.Column("disco_total_gb", sa.String(), nullable=True),
            sa.Column("disco_livre_gb", sa.String(), nullable=True),
            sa.Column("agent_version", sa.String(), nullable=True),
            sa.Column("ultimo_boot", sa.DateTime(), nullable=True),
            sa.Column("ultima_comunicacao", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )

    create_index_if_missing("ix_assets_id", "assets", ["id"])
    create_index_if_missing("ix_assets_hostname", "assets", ["hostname"])
    create_index_if_missing("ix_assets_serial", "assets", ["serial"])
    create_index_if_missing("ix_assets_mac_address", "assets", ["mac_address"])
    create_index_if_missing("ix_users_id", "users", ["id"])
    create_index_if_missing("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    drop_index_if_exists("ix_users_username", "users")
    drop_index_if_exists("ix_users_id", "users")
    drop_index_if_exists("ix_assets_mac_address", "assets")
    drop_index_if_exists("ix_assets_serial", "assets")
    drop_index_if_exists("ix_assets_hostname", "assets")
    drop_index_if_exists("ix_assets_id", "assets")

    if table_exists("users"):
        op.drop_table("users")

    if table_exists("assets"):
        op.drop_table("assets")
