"""endurecimento de segurança (T-703): FKs compostas por firm_id e função de sync sem payload

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-17

- B3: referências entre tabelas de negócio passam a exigir o mesmo firm_id (FK composta),
  para que nem um bug de código ligue dados de escritórios diferentes.
- B1: tracing_traces_com_falha deixa de devolver entrada/saída/decisão (só metadados) e tem
  limite máximo; o reenvio ao Langfuse manda apenas o resumo técnico.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tabela, fk antiga, colunas locais, tabela alvo)
FKS_TRACE = (
    ("agent_decisions", "agent_decisions_trace_id_fkey"),
    ("evals_gold", "evals_gold_trace_id_fkey"),
    ("evals_human", "evals_human_trace_id_fkey"),
    ("pgdas_documents", "pgdas_documents_trace_id_fkey"),
    ("simulations", "simulations_trace_id_fkey"),
)


def upgrade() -> None:
    op.create_unique_constraint("uq_agent_traces_id_firm", "agent_traces", ["id", "firm_id"])
    op.create_unique_constraint("uq_pgdas_id_firm", "pgdas_documents", ["id", "firm_id"])
    for tabela, fk in FKS_TRACE:
        op.drop_constraint(fk, tabela, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{tabela}_trace_firm",
            tabela,
            "agent_traces",
            ["trace_id", "firm_id"],
            ["id", "firm_id"],
        )
    op.drop_constraint("fk_movements_pgdas_document", "monthly_movements", type_="foreignkey")
    op.create_foreign_key(
        "fk_movements_pgdas_document_firm",
        "monthly_movements",
        "pgdas_documents",
        ["pgdas_document_id", "firm_id"],
        ["id", "firm_id"],
    )
    op.create_foreign_key(
        "fk_agent_traces_company_firm",
        "agent_traces",
        "companies",
        ["company_id", "firm_id"],
        ["id", "firm_id"],
    )
    op.execute("DROP FUNCTION IF EXISTS tracing_traces_com_falha(integer)")
    op.execute(
        """
        CREATE FUNCTION tracing_traces_com_falha(p_limite integer)
        RETURNS TABLE (
            id text, agente text, gatilho text, status status_trace, criado_em timestamptz
        )
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT id, agente, gatilho, status, criado_em
            FROM agent_traces WHERE langfuse_sync = 'failed'
            ORDER BY criado_em LIMIT least(greatest(p_limite, 0), 100)
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION tracing_traces_com_falha(integer) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION tracing_traces_com_falha(integer) TO fator_r_app")


def downgrade() -> None:
    op.drop_constraint("fk_agent_traces_company_firm", "agent_traces", type_="foreignkey")
    op.drop_constraint("fk_movements_pgdas_document_firm", "monthly_movements", type_="foreignkey")
    op.create_foreign_key(
        "fk_movements_pgdas_document",
        "monthly_movements",
        "pgdas_documents",
        ["pgdas_document_id"],
        ["id"],
    )
    for tabela, fk in FKS_TRACE:
        op.drop_constraint(f"fk_{tabela}_trace_firm", tabela, type_="foreignkey")
        op.create_foreign_key(fk, tabela, "agent_traces", ["trace_id"], ["id"])
    op.drop_constraint("uq_pgdas_id_firm", "pgdas_documents", type_="unique")
    op.drop_constraint("uq_agent_traces_id_firm", "agent_traces", type_="unique")
