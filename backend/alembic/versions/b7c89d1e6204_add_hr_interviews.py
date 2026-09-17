"""Add HR practice sessions with fictional candidates.

Revision ID: b7c89d1e6204
Revises: 9f2a4c1b7e30
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c89d1e6204"
down_revision = "9f2a4c1b7e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hr_interviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("turns", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("hr_interviews")
