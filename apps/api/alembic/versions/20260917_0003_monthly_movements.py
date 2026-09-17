"""monthly_movements (T-102)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17

pgdas_document_id nasce sem FK: a tabela pgdas_documents chega no M5 (T-501),
que adiciona a FK numa migração nova.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VALORES = ("receita_bruta", "pro_labore", "salarios", "cpp", "fgts")


def upgrade() -> None:
    origem = postgresql.ENUM(
        "manual", "pgdas", "folha", "agente", name="origem_movimento", create_type=True
    )
    origem.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "monthly_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competencia", sa.Date(), nullable=False),
        *[
            sa.Column(nome, sa.Numeric(14, 2), nullable=False, server_default="0")
            for nome in VALORES
        ],
        sa.Column(
            "folha_mes",
            sa.Numeric(14, 2),
            sa.Computed("pro_labore + salarios + cpp + fgts", persisted=True),
        ),
        sa.Column(
            "origem", postgresql.ENUM(name="origem_movimento", create_type=False), nullable=False
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("pgdas_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "firm_id"],
            ["companies.id", "companies.firm_id"],
            name="fk_movements_company_firm",
        ),
        sa.UniqueConstraint("company_id", "competencia", name="uq_movements_company_competencia"),
        sa.CheckConstraint(
            "extract(day FROM competencia) = 1", name="ck_movements_competencia_dia1"
        ),
        *[sa.CheckConstraint(f"{nome} >= 0", name=f"ck_movements_{nome}") for nome in VALORES],
    )
    op.create_index("ix_movements_firm_id", "monthly_movements", ["firm_id"])


def downgrade() -> None:
    op.drop_table("monthly_movements")
    postgresql.ENUM(name="origem_movimento").drop(op.get_bind(), checkfirst=True)
