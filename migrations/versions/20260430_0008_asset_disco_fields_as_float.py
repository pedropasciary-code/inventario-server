"""asset disco fields as float

Revision ID: 20260430_0008
Revises: 20260429_0007
Create Date: 2026-04-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0008"
down_revision: Union[str, None] = "20260429_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for column in ("disco_total_gb", "disco_livre_gb"):
            op.execute(
                sa.text(
                    f"""
                    UPDATE assets
                    SET {column} = NULL
                    WHERE btrim({column}) = ''
                       OR replace({column}, ',', '.') !~ '^[+-]?([0-9]+(\\.[0-9]*)?|\\.[0-9]+)$'
                    """
                )
            )

    op.alter_column(
        "assets",
        "disco_total_gb",
        type_=sa.Float(),
        existing_type=sa.String(),
        postgresql_using="NULLIF(replace(disco_total_gb, ',', '.'), '')::DOUBLE PRECISION",
        existing_nullable=True,
    )
    op.alter_column(
        "assets",
        "disco_livre_gb",
        type_=sa.Float(),
        existing_type=sa.String(),
        postgresql_using="NULLIF(replace(disco_livre_gb, ',', '.'), '')::DOUBLE PRECISION",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "assets",
        "disco_total_gb",
        type_=sa.String(),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "assets",
        "disco_livre_gb",
        type_=sa.String(),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
