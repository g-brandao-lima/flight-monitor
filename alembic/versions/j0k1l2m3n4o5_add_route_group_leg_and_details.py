"""add route_group_legs table and flight_snapshots.details column

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_group_legs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "route_group_id",
            sa.Integer(),
            sa.ForeignKey("route_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=3), nullable=False),
        sa.Column("destination", sa.String(length=3), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("min_stay_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_stay_days", sa.Integer(), nullable=True),
        sa.Column("max_stops", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_route_group_legs_group_order",
        "route_group_legs",
        ["route_group_id", "order"],
        unique=True,
    )
    op.add_column(
        "flight_snapshots",
        sa.Column("details", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("flight_snapshots", "details")
    op.drop_index("ix_route_group_legs_group_order", table_name="route_group_legs")
    op.drop_table("route_group_legs")
