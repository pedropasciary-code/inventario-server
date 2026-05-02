"""normalize usernames

Revision ID: 20260501_0009
Revises: 20260430_0008
Create Date: 2026-05-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260501_0009"
down_revision: Union[str, None] = "20260430_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT lower(username) AS normalized_username
            FROM users
            GROUP BY lower(username)
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        names = ", ".join(row.normalized_username for row in duplicates)
        raise RuntimeError(
            "Cannot normalize usernames because case-insensitive duplicates exist: "
            f"{names}"
        )

    op.execute(sa.text("UPDATE users SET username = lower(username)"))


def downgrade() -> None:
    pass
