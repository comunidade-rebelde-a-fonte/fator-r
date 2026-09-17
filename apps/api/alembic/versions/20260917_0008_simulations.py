"""simulations (T-603)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from fator_r.core.rls_sql import enable_rls, grant_app

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    postgresql.ENUM("ja_na_meta", "corrigir", "nao_forcar", name="veredito_simulacao").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "simulations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pa", sa.Date(), nullable=False),
        sa.Column("parametros_json", postgresql.JSONB(), nullable=False),
        sa.Column("resultado_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "veredito", postgresql.ENUM(name="veredito_simulacao", create_type=False), nullable=True
        ),
        sa.Column("trace_id", sa.String(32), sa.ForeignKey("agent_traces.id"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "firm_id"],
            ["companies.id", "companies.firm_id"],
            name="fk_simulations_company_firm",
        ),
        sa.CheckConstraint("extract(day FROM pa) = 1", name="ck_simulations_pa_dia1"),
    )
    op.create_index("ix_simulations_company", "simulations", ["company_id", "criado_em"])
    op.execute(grant_app("simulations", "SELECT, INSERT"))
    for statement in enable_rls("simulations"):
        op.execute(statement)


def downgrade() -> None:
    op.drop_table("simulations")
    postgresql.ENUM(name="veredito_simulacao").drop(op.get_bind(), checkfirst=True)
