import httpx
from sqlalchemy import func, select

from fator_r.core.db import get_owner_sessionmaker
from fator_r.repositories.orm import Firm, User
from fator_r.seed import SeedConfig, seed

CONFIG = SeedConfig(
    firm_nome="Escritório Piloto",
    user_email="analista@escritorio-piloto.com.br",
    user_nome="Analista",
    user_senha="senha-do-seed-123",
)


async def test_seed_cria_escritorio_com_padroes_e_usuario_que_loga(
    client: httpx.AsyncClient,
) -> None:
    async with get_owner_sessionmaker()() as session:
        resultado = await seed(session, CONFIG)
    assert resultado.firm_criado
    assert resultado.user_criado

    async with get_owner_sessionmaker()() as session:
        firm = (await session.execute(select(Firm))).scalar_one()
    assert str(firm.meta_operacional) == "0.300000"
    assert str(firm.limiar_confianca_parser) == "0.400000"
    assert str(firm.piso_economia_anual) == "6000.00"
    assert firm.cpp_das_integra_fs12 is True
    assert str(firm.tolerancia_ouro_pct) == "0.010000"

    response = await client.post(
        "/auth/login", json={"email": CONFIG.user_email, "senha": CONFIG.user_senha}
    )
    assert response.status_code == 200


async def test_seed_e_idempotente() -> None:
    async with get_owner_sessionmaker()() as session:
        await seed(session, CONFIG)
    async with get_owner_sessionmaker()() as session:
        segundo = await seed(session, CONFIG)
    assert not segundo.firm_criado
    assert not segundo.user_criado
    async with get_owner_sessionmaker()() as session:
        assert (await session.execute(select(func.count()).select_from(Firm))).scalar_one() == 1
        assert (await session.execute(select(func.count()).select_from(User))).scalar_one() == 1
