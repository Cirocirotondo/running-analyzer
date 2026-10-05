"""Playback Video flag on videos, Failure Report on analyses

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-04 23:50:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("playback", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("analyses", sa.Column("failure_report", sa.String(8), nullable=True))
    op.add_column("analyses", sa.Column("failure_report_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "failure_report_at")
    op.drop_column("analyses", "failure_report")
    op.drop_column("videos", "playback")
