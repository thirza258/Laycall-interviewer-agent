"""add evaluation score range checks

The score bounds live on the model as column CheckConstraints, but alembic's
autogenerate does not detect check constraints, so the initial migration
created the table without them: the database accepted a technical_score of 87
while create_all() (and therefore the test suite) rejected it.

Revision ID: 9f2a4c1b7e30
Revises: 7105229cf429
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f2a4c1b7e30'
down_revision: Union[str, Sequence[str], None] = '7105229cf429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_evaluations_technical_score_range",
        "evaluations",
        "technical_score >= 0 AND technical_score <= 10",
    )
    op.create_check_constraint(
        "ck_evaluations_communication_score_range",
        "evaluations",
        "communication_score >= 0 AND communication_score <= 10",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_evaluations_communication_score_range", "evaluations", type_="check"
    )
    op.drop_constraint(
        "ck_evaluations_technical_score_range", "evaluations", type_="check"
    )
