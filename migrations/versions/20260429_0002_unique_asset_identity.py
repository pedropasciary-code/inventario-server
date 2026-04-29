"""enforce unique asset identity

Revision ID: 20260429_0002
Revises: 20260429_0001
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260429_0002"
down_revision: Union[str, None] = "20260429_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def drop_index_if_exists(index_name: str, table_name: str):
    if index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def create_index_if_missing(index_name: str, table_name: str, columns: list[str], unique: bool = False):
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def ensure_no_duplicate_values(table_name: str, column_name: str):
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            f"""
            SELECT {column_name}, COUNT(*) AS total
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
            GROUP BY {column_name}
            HAVING COUNT(*) > 1
            LIMIT 5
            """
        )
    ).fetchall()

    if duplicates:
        values = ", ".join(str(row[0]) for row in duplicates)
        raise RuntimeError(
            f"Nao foi possivel criar indice unico em {table_name}.{column_name}. "
            f"Resolva os valores duplicados antes de migrar: {values}"
        )


def upgrade() -> None:
    ensure_no_duplicate_values("assets", "serial")
    ensure_no_duplicate_values("assets", "mac_address")

    drop_index_if_exists("ix_assets_serial", "assets")
    drop_index_if_exists("ix_assets_mac_address", "assets")

    create_index_if_missing("ix_assets_serial", "assets", ["serial"], unique=True)
    create_index_if_missing("ix_assets_mac_address", "assets", ["mac_address"], unique=True)


def downgrade() -> None:
    drop_index_if_exists("ix_assets_mac_address", "assets")
    drop_index_if_exists("ix_assets_serial", "assets")

    create_index_if_missing("ix_assets_serial", "assets", ["serial"])
    create_index_if_missing("ix_assets_mac_address", "assets", ["mac_address"])
