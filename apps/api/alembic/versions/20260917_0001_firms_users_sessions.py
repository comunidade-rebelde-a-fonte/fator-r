"""firms, users e sessions (T-008)

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("meta_operacional", sa.Numeric(7, 6), nullable=False),
        sa.Column("limiar_confianca_parser", sa.Numeric(7, 6), nullable=False),
        sa.Column("piso_economia_anual", sa.Numeric(14, 2), nullable=False),
        sa.Column("cpp_das_integra_fs12", sa.Boolean(), nullable=False),
        sa.Column("tolerancia_ouro_pct", sa.Numeric(7, 6), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "meta_operacional >= 0.28 AND meta_operacional < 1", name="ck_firms_meta"
        ),
        sa.CheckConstraint(
            "limiar_confianca_parser > 0 AND limiar_confianca_parser <= 1", name="ck_firms_limiar"
        ),
        sa.CheckConstraint("piso_economia_anual >= 0", name="ck_firms_piso"),
        sa.CheckConstraint(
            "tolerancia_ouro_pct >= 0 AND tolerancia_ouro_pct < 1", name="ck_firms_tolerancia"
        ),
    )
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_firm_id", "users", ["firm_id"])
    op.execute("CREATE UNIQUE INDEX ux_users_email_lower ON users (lower(email))")
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_index("ux_users_email_lower", table_name="users")
    op.drop_table("users")
    op.drop_table("firms")
