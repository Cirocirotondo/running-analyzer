"""Left and Right Side Views, upload slots, per-view whole-body metrics, unreliable flag

Revision ID: b1c2d3e4f5a6
Revises: 7cb6e0d0de27
Create Date: 2026-10-04 19:30:00

Existing side Videos become left_side / right_side from the near leg their Analysis found; keys of the
Analysis' window, camera_check and keypoints_keys follow.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "7cb6e0d0de27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("videos", "view", type_=sa.String(16))
    op.add_column("videos", sa.Column("slot", sa.String(8), nullable=True))
    op.execute("UPDATE videos SET slot = CASE WHEN view = 'rear' THEN 'rear' ELSE 'side_a' END")
    op.alter_column("videos", "slot", nullable=False)
    op.add_column("metric_values", sa.Column("per_view", JSONB(), nullable=True))
    op.add_column("metric_values", sa.Column("unreliable_reason", sa.String(32), nullable=True))
    # Resolve the side of analysed side Videos from the near leg.
    op.execute("""
        UPDATE videos v SET view = CASE a.camera_check->'side'->>'near_side' WHEN 'L' THEN 'left_side' WHEN 'R' THEN 'right_side' END
        FROM analyses a
        WHERE a.session_id = v.session_id AND v.view = 'side' AND a.camera_check->'side'->>'near_side' IN ('L', 'R')
    """)
    for col in ("window", "camera_check", "keypoints_keys"):
        op.execute(f"""
            UPDATE analyses a SET "{col}" = ("{col}" - 'side') || jsonb_build_object(v.view, "{col}"->'side')
            FROM videos v
            WHERE v.session_id = a.session_id AND v.slot = 'side_a' AND v.view IN ('left_side', 'right_side')
              AND "{col}" ? 'side'
        """)


def downgrade() -> None:
    for col in ("window", "camera_check", "keypoints_keys"):
        for view in ("left_side", "right_side"):
            op.execute(f"""UPDATE analyses SET "{col}" = ("{col}" - '{view}') || jsonb_build_object('side', "{col}"->'{view}') WHERE "{col}" ? '{view}'""")
    op.execute("UPDATE videos SET view = 'side' WHERE view IN ('left_side', 'right_side')")
    op.drop_column("metric_values", "unreliable_reason")
    op.drop_column("metric_values", "per_view")
    op.drop_column("videos", "slot")
    op.alter_column("videos", "view", type_=sa.String(8))
