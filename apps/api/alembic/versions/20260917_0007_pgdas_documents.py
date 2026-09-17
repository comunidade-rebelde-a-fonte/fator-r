"""pgdas_documents e FK de monthly_movements.pgdas_document_id (T-501)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from fator_r.core.rls_sql import enable_rls, grant_app

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS = ("received", "parsed", "needs_review", "linked", "rejected")


def upgrade() -> None:
    postgresql.ENUM(*STATUS, name="status_documento").create(op.get_bind(), checkfirst=True)
    op.create_table(
        "pgdas_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("arquivo_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("nome_original", sa.Text(), nullable=True),
        sa.Column("texto_extraido", sa.Text(), nullable=True),
        sa.Column("campos_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "status", postgresql.ENUM(name="status_documento", create_type=False), nullable=False
        ),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(32), sa.ForeignKey("agent_traces.id"), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("firm_id", "sha256", name="uq_pgdas_firm_sha256"),
        sa.ForeignKeyConstraint(
            ["company_id", "firm_id"],
            ["companies.id", "companies.firm_id"],
            name="fk_pgdas_company_firm",
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_pgdas_sha256"),
        sa.CheckConstraint("mime IN ('application/pdf', 'text/plain')", name="ck_pgdas_mime"),
        sa.CheckConstraint(
            "confianca IS NULL OR confianca BETWEEN 0 AND 1", name="ck_pgdas_confianca"
        ),
    )
    op.create_index("ix_pgdas_firm_status", "pgdas_documents", ["firm_id", "status"])
    op.execute(grant_app("pgdas_documents"))
    for statement in enable_rls("pgdas_documents"):
        op.execute(statement)
    op.create_foreign_key(
        "fk_movements_pgdas_document",
        "monthly_movements",
        "pgdas_documents",
        ["pgdas_document_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_movements_pgdas_document", "monthly_movements", type_="foreignkey")
    op.drop_table("pgdas_documents")
    postgresql.ENUM(name="status_documento").drop(op.get_bind(), checkfirst=True)
