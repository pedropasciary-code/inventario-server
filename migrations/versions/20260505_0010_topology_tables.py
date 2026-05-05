"""add topology tables

Revision ID: 20260505_0010
Revises: 20260501_0009
Create Date: 2026-05-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260505_0010"
down_revision: Union[str, None] = "20260501_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topologies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topologies_id", "topologies", ["id"])

    op.create_table(
        "topology_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topology_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("node_type", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("props_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topology_id"], ["topologies.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["topology_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topology_nodes_id", "topology_nodes", ["id"])
    op.create_index("ix_topology_nodes_topology_id", "topology_nodes", ["topology_id"])

    op.create_table(
        "topology_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topology_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("connection_type", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["topology_id"], ["topologies.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["topology_nodes.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["topology_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topology_edges_id", "topology_edges", ["id"])
    op.create_index("ix_topology_edges_topology_id", "topology_edges", ["topology_id"])


def downgrade() -> None:
    op.drop_index("ix_topology_edges_topology_id", table_name="topology_edges")
    op.drop_index("ix_topology_edges_id", table_name="topology_edges")
    op.drop_table("topology_edges")
    op.drop_index("ix_topology_nodes_topology_id", table_name="topology_nodes")
    op.drop_index("ix_topology_nodes_id", table_name="topology_nodes")
    op.drop_table("topology_nodes")
    op.drop_index("ix_topologies_id", table_name="topologies")
    op.drop_table("topologies")
