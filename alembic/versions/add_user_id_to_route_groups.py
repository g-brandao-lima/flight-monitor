"""add user_id to route_groups

Revision ID: a1b2c3d4e5f6
Revises: 86a799448829
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "86a799448829"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("route_groups", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_route_groups_user_id", "route_groups", ["user_id"])
    op.create_foreign_key(
        "fk_route_groups_user_id", "route_groups", "users", ["user_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_route_groups_user_id", "route_groups", type_="foreignkey")
    op.drop_index("ix_route_groups_user_id", table_name="route_groups")
    op.drop_column("route_groups", "user_id")
