from datetime import date
from decimal import Decimal

import pytest

from fator_r.core.db import get_owner_sessionmaker, get_sessionmaker
from fator_r.domain.tabelas import TabelaNaoVigente
from fator_r.repositories.simples_tables import carregar_csv, tabela_vigente


async def test_seed_das_tabelas_e_idempotente() -> None:
    async with get_owner_sessionmaker()() as session:
        assert await carregar_csv(session) == 0  # já carregado na preparação dos testes


async def test_tabela_vigente_pela_data() -> None:
    async with get_sessionmaker()() as session:
        iii = await tabela_vigente(session, "III", date(2026, 9, 1))
        v = await tabela_vigente(session, "V", date(2018, 1, 1))  # exatamente no início
    assert iii.vigencia_inicio == date(2018, 1, 1)
    assert len(iii.faixas) == 6
    assert len(v.faixas) == 6
    assert iii.faixa_para(Decimal("180000.00")).faixa == 1  # type: ignore[union-attr]
    assert iii.faixa_para(Decimal("180000.01")).faixa == 2  # type: ignore[union-attr]
    assert iii.faixa_para(Decimal("4800000.01")) is None


async def test_sem_vigencia_falha_explicitamente() -> None:
    async with get_sessionmaker()() as session:
        with pytest.raises(TabelaNaoVigente):
            await tabela_vigente(session, "III", date(2017, 12, 1))
