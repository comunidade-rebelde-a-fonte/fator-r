"""RLS: a role da aplicação só enxerga o escritório de app.firm_id (T-103)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from fator_r.core.db import firm_session, get_owner_sessionmaker, get_sessionmaker
from fator_r.repositories.orm import Company, MonthlyMovement
from tests.factories import criar_escritorio_com_usuario


async def _empresa_com_movimento(firm_id: uuid.UUID, cnpj: str) -> uuid.UUID:
    from datetime import date

    async with get_owner_sessionmaker()() as session:
        company = Company(firm_id=firm_id, nome=f"Empresa {cnpj}", cnpj=cnpj, sujeita_fator_r=True)
        session.add(company)
        await session.flush()
        session.add(
            MonthlyMovement(
                firm_id=firm_id,
                company_id=company.id,
                competencia=date(2026, 1, 1),
                receita_bruta=Decimal("1000"),
                origem="manual",
            )
        )
        await session.commit()
        return company.id


async def test_query_crua_sem_filtro_so_ve_o_proprio_escritorio() -> None:
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    await _empresa_com_movimento(a.firm_id, "11222333000181")
    await _empresa_com_movimento(b.firm_id, "45723174000110")

    async with firm_session(a.firm_id) as session:
        for tabela in ("companies", "monthly_movements", "users"):
            firms = (await session.execute(text(f"SELECT DISTINCT firm_id FROM {tabela}"))).all()  # noqa: S608
            assert [row[0] for row in firms] == [a.firm_id], tabela
        firms = (await session.execute(text("SELECT id FROM firms"))).all()
        assert [row[0] for row in firms] == [a.firm_id]


async def test_sem_app_firm_id_nao_ve_nada() -> None:
    a = await criar_escritorio_com_usuario()
    await _empresa_com_movimento(a.firm_id, "11222333000181")
    async with get_sessionmaker()() as session:
        for tabela in ("companies", "monthly_movements", "users", "firms"):
            total = (await session.execute(text(f"SELECT count(*) FROM {tabela}"))).scalar_one()  # noqa: S608
            assert total == 0, tabela


async def test_nao_consegue_inserir_para_outro_escritorio() -> None:
    a = await criar_escritorio_com_usuario("a@escritorio-a.com.br")
    b = await criar_escritorio_com_usuario("b@escritorio-b.com.br")
    async with firm_session(a.firm_id) as session:
        session.add(
            Company(firm_id=b.firm_id, nome="Intrusa", cnpj="45723174000110", sujeita_fator_r=True)
        )
        with pytest.raises(DBAPIError, match="row-level security"):
            await session.commit()


async def test_role_da_aplicacao_nao_ignora_rls() -> None:
    async with get_sessionmaker()() as session:
        row = (
            await session.execute(
                text("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    assert row == (False, False)


async def test_role_da_aplicacao_nao_apaga_movimentos() -> None:
    a = await criar_escritorio_com_usuario()
    await _empresa_com_movimento(a.firm_id, "11222333000181")
    async with firm_session(a.firm_id) as session:
        with pytest.raises(DBAPIError, match="permission denied"):
            await session.execute(text("DELETE FROM monthly_movements"))


async def test_coluna_gerada_folha_mes() -> None:
    a = await criar_escritorio_com_usuario()
    from datetime import date

    async with get_owner_sessionmaker()() as session:
        company = Company(firm_id=a.firm_id, nome="X", cnpj="11222333000181", sujeita_fator_r=True)
        session.add(company)
        await session.flush()
        session.add(
            MonthlyMovement(
                firm_id=a.firm_id,
                company_id=company.id,
                competencia=date(2026, 2, 1),
                pro_labore=Decimal("1000.10"),
                salarios=Decimal("2000.20"),
                cpp=Decimal("300.30"),
                fgts=Decimal("160.40"),
                origem="manual",
            )
        )
        await session.commit()
        folha = (
            await session.execute(text("SELECT folha_mes FROM monthly_movements"))
        ).scalar_one()
    assert folha == Decimal("3461.00")
