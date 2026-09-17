"""Retenção mínima de 24 meses (T-702, PRD §8): nada apaga dados de negócio ou traces."""

import re
from pathlib import Path

from sqlalchemy import text

from fator_r.core.db import get_owner_sessionmaker

API = Path(__file__).resolve().parents[2]
PROTEGIDAS = (
    "companies",
    "monthly_movements",
    "agent_traces",
    "agent_decisions",
    "pgdas_documents",
    "simulations",
    "evals_gold",
    "evals_human",
    "firms",
    "users",
)


def test_codigo_da_aplicacao_nao_apaga_tabelas_protegidas() -> None:
    padrao = re.compile(
        r"(DELETE\s+FROM|TRUNCATE)\s+("
        + "|".join(PROTEGIDAS)
        + r")\b|delete\(("
        + "|".join(
            [
                "Company",
                "MonthlyMovement",
                "AgentTrace",
                "AgentDecision",
                "PgdasDocument",
                "Simulation",
                "EvalGold",
                "EvalHuman",
                "Firm",
                "User",
            ]
        )
        + r")\)",
        re.IGNORECASE,
    )
    achados = [
        f"{arquivo.relative_to(API)}:{n}"
        for arquivo in (API / "src").rglob("*.py")
        for n, linha in enumerate(arquivo.read_text().splitlines(), start=1)
        if padrao.search(linha)
    ]
    assert achados == []


async def test_role_da_aplicacao_nao_tem_delete_nem_truncate_nas_tabelas_protegidas() -> None:
    async with get_owner_sessionmaker()() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
                    "WHERE grantee = 'fator_r_app' AND privilege_type IN ('DELETE', 'TRUNCATE')"
                )
            )
        ).all()
    assert {r[0] for r in rows} <= {"sessions"}
