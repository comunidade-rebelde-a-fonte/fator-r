"""agent_traces, agent_decisions, evals_gold, evals_human (T-402)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from fator_r.core.rls_sql import APP_ROLE, enable_rls, grant_app

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS = {
    "status_trace": ("ok", "error", "needs_review"),
    "langfuse_sync": ("pending", "ok", "failed"),
    "status_eval_ouro": ("ok", "erro", "ouro_indisponivel"),
    "nota_humana": ("acerto", "parcial", "erro"),
}


def _enum(nome: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=nome, create_type=False)


def _uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _criado_em() -> sa.Column[object]:
    return sa.Column(
        "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def _trace_fk() -> sa.Column[object]:
    return sa.Column("trace_id", sa.String(32), sa.ForeignKey("agent_traces.id"), nullable=False)


def upgrade() -> None:
    for nome, valores in ENUMS.items():
        postgresql.ENUM(*valores, name=nome).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        sa.Column("agente", sa.Text(), nullable=False),
        sa.Column("gatilho", sa.Text(), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entrada_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("saida_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("decisao_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", _enum("status_trace"), nullable=False),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column(
            "langfuse_sync", _enum("langfuse_sync"), nullable=False, server_default="pending"
        ),
        _criado_em(),
        sa.CheckConstraint("id ~ '^[0-9a-f]{32}$'", name="ck_agent_traces_id_hex"),
        sa.CheckConstraint("confianca IS NULL OR confianca BETWEEN 0 AND 1", name="ck_traces_conf"),
    )
    op.create_index("ix_agent_traces_firm_criado", "agent_traces", ["firm_id", "criado_em"])
    op.create_index("ix_agent_traces_sync", "agent_traces", ["langfuse_sync"])

    op.create_table(
        "agent_decisions",
        _uuid_pk(),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        _trace_fk(),
        sa.Column("agente", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("dados_json", postgresql.JSONB(), nullable=False),
        _criado_em(),
    )
    op.create_index("ix_agent_decisions_trace", "agent_decisions", ["trace_id"])

    op.create_table(
        "evals_gold",
        _uuid_pk(),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        _trace_fk(),
        sa.Column("campo", sa.Text(), nullable=False),
        sa.Column("esperado", sa.Text(), nullable=True),
        sa.Column("obtido", sa.Text(), nullable=True),
        sa.Column("dentro_tolerancia", sa.Boolean(), nullable=True),
        sa.Column("status", _enum("status_eval_ouro"), nullable=False),
        _criado_em(),
    )
    op.create_index("ix_evals_gold_trace", "evals_gold", ["trace_id"])

    op.create_table(
        "evals_human",
        _uuid_pk(),
        sa.Column(
            "firm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=False
        ),
        _trace_fk(),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("nota", _enum("nota_humana"), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        _criado_em(),
        sa.CheckConstraint(
            "nota <> 'erro' OR (comentario IS NOT NULL AND length(trim(comentario)) > 0)",
            name="ck_evals_human_comentario_em_erro",
        ),
    )
    op.create_index("ix_evals_human_trace", "evals_human", ["trace_id"])

    for tabela in ("agent_traces", "agent_decisions", "evals_gold", "evals_human"):
        op.execute(
            grant_app(
                tabela, "SELECT, INSERT, UPDATE" if tabela == "agent_traces" else "SELECT, INSERT"
            )
        )
        for statement in enable_rls(tabela):
            op.execute(statement)

    # Rotinas de sistema (sync com o Langfuse) sem escritório no contexto: só estas funções.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION tracing_marcar_sync(p_ids text[], p_status langfuse_sync)
        RETURNS integer LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            WITH alterados AS (
                UPDATE agent_traces SET langfuse_sync = p_status
                WHERE id = ANY(p_ids) AND langfuse_sync <> p_status
                RETURNING 1
            )
            SELECT count(*)::integer FROM alterados
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION tracing_traces_com_falha(p_limite integer)
        RETURNS TABLE (
            id text, firm_id uuid, agente text, gatilho text, status status_trace,
            entrada_json jsonb, saida_json jsonb, decisao_json jsonb, criado_em timestamptz
        )
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT id, firm_id, agente, gatilho, status, entrada_json, saida_json, decisao_json,
                   criado_em
            FROM agent_traces WHERE langfuse_sync = 'failed'
            ORDER BY criado_em LIMIT p_limite
        $$;
        """
    )
    for fn in ("tracing_marcar_sync(text[], langfuse_sync)", "tracing_traces_com_falha(integer)"):
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS tracing_traces_com_falha(integer)")
    op.execute("DROP FUNCTION IF EXISTS tracing_marcar_sync(text[], langfuse_sync)")
    for tabela in ("evals_human", "evals_gold", "agent_decisions", "agent_traces"):
        op.drop_table(tabela)
    for nome in ENUMS:
        postgresql.ENUM(name=nome).drop(op.get_bind(), checkfirst=True)
