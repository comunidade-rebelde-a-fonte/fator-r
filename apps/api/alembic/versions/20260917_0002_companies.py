"""companies (T-101)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pacote = postgresql.ENUM(
        "monitoramento", "correcao", "retainer", name="pacote_comercial", create_type=True
    )
    pacote.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("cnae", sa.Text(), nullable=True),
        sa.Column("atividade", sa.Text(), nullable=True),
        sa.Column("sujeita_fator_r", sa.Boolean(), nullable=False),
        sa.Column("qtd_socios", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("contato", sa.Text(), nullable=True),
        sa.Column(
            "pacote",
            postgresql.ENUM(name="pacote_comercial", create_type=False),
            nullable=True,
        ),
        sa.Column("honorario_mensal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("inicio_atividade", sa.Date(), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("firm_id", "cnpj", name="uq_companies_firm_cnpj"),
        sa.UniqueConstraint("id", "firm_id", name="uq_companies_id_firm"),
        sa.CheckConstraint("cnpj ~ '^[0-9]{14}$'", name="ck_companies_cnpj_digitos"),
        sa.CheckConstraint("qtd_socios >= 0", name="ck_companies_qtd_socios"),
        sa.CheckConstraint("honorario_mensal >= 0", name="ck_companies_honorario"),
        sa.CheckConstraint(
            "inicio_atividade IS NULL OR extract(day FROM inicio_atividade) = 1",
            name="ck_companies_inicio_dia1",
        ),
    )


def downgrade() -> None:
    op.drop_table("companies")
    postgresql.ENUM(name="pacote_comercial").drop(op.get_bind(), checkfirst=True)
