"""simples_tables com vigência (T-201)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17

Tabela de referência legal (não é dado de escritório): sem firm_id e sem RLS;
a role da aplicação só lê.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from fator_r.core.rls_sql import grant_app

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    anexo = postgresql.ENUM("III", "V", name="anexo_simples", create_type=True)
    anexo.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "simples_tables",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "anexo", postgresql.ENUM(name="anexo_simples", create_type=False), nullable=False
        ),
        sa.Column("faixa", sa.SmallInteger(), nullable=False),
        sa.Column("rbt12_ate", sa.Numeric(14, 2), nullable=False),
        sa.Column("aliquota_nominal", sa.Numeric(7, 6), nullable=False),
        sa.Column("parcela_deduzir", sa.Numeric(14, 2), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.UniqueConstraint("anexo", "faixa", "vigencia_inicio", name="uq_simples_faixa_vigencia"),
        sa.CheckConstraint(
            "vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio", name="ck_simples_vigencia"
        ),
        sa.CheckConstraint("faixa BETWEEN 1 AND 6", name="ck_simples_faixa"),
        sa.CheckConstraint(
            "aliquota_nominal > 0 AND aliquota_nominal < 1", name="ck_simples_aliquota"
        ),
        sa.CheckConstraint("rbt12_ate > 0 AND parcela_deduzir >= 0", name="ck_simples_valores"),
    )
    op.execute(grant_app("simples_tables", "SELECT"))


def downgrade() -> None:
    op.drop_table("simples_tables")
    postgresql.ENUM(name="anexo_simples").drop(op.get_bind(), checkfirst=True)
