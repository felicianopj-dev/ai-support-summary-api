"""Create ticket analyses table.

Revision ID: 20260618_0003
Revises: 20260616_0002
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260618_0003"
down_revision: str | Sequence[str] | None = "20260616_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index(
        op.f("ix_ticket_analyses_ticket_id"),
        "ticket_analyses",
        ["ticket_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ticket_analyses_ticket_id"), table_name="ticket_analyses")
    op.drop_table("ticket_analyses")
