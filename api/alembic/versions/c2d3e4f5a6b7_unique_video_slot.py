"""One Video per upload slot (two side Videos are both "side" until recognized)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-04 19:50:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("videos_session_id_view_key", "videos", type_="unique")
    op.create_unique_constraint("videos_session_id_slot_key", "videos", ["session_id", "slot"])


def downgrade() -> None:
    op.drop_constraint("videos_session_id_slot_key", "videos", type_="unique")
    op.create_unique_constraint("videos_session_id_view_key", "videos", ["session_id", "view"])
