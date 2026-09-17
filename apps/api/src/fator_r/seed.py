"""Seed inicial idempotente: um escritório e um usuário (T-011).

Uso: python -m fator_r.seed  (variáveis SEED_* no ambiente; a senha nunca fica no código)
Rodar de novo não duplica nem altera o que já existe.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.core.db import get_owner_engine, get_owner_sessionmaker
from fator_r.core.security import hash_password
from fator_r.repositories.orm import Firm, User
from fator_r.repositories.simples_tables import carregar_csv

# Padrões do escritório (Plano §4 e Registro de decisões de 2026-09-17).
META_OPERACIONAL = Decimal("0.30")
LIMIAR_CONFIANCA_PARSER = Decimal("0.40")
PISO_ECONOMIA_ANUAL = Decimal("6000.00")
CPP_DAS_INTEGRA_FS12 = True
TOLERANCIA_OURO_PCT = Decimal("0.01")


@dataclass(frozen=True)
class SeedConfig:
    firm_nome: str
    user_email: str
    user_nome: str
    user_senha: str

    @classmethod
    def from_env(cls) -> "SeedConfig":
        faltando = [
            nome
            for nome in (
                "SEED_FIRM_NOME",
                "SEED_USER_EMAIL",
                "SEED_USER_NOME",
                "SEED_USER_PASSWORD",
            )
            if not os.environ.get(nome)
        ]
        if faltando:
            raise SystemExit(f"Variáveis obrigatórias ausentes: {', '.join(faltando)}")
        return cls(
            firm_nome=os.environ["SEED_FIRM_NOME"],
            user_email=os.environ["SEED_USER_EMAIL"],
            user_nome=os.environ["SEED_USER_NOME"],
            user_senha=os.environ["SEED_USER_PASSWORD"],
        )


@dataclass(frozen=True)
class SeedResultado:
    firm_criado: bool
    user_criado: bool
    faixas_inseridas: int = 0


async def seed(session: AsyncSession, config: SeedConfig) -> SeedResultado:
    faixas_inseridas = await carregar_csv(session)
    firm = (
        await session.execute(select(Firm).where(Firm.nome == config.firm_nome))
    ).scalar_one_or_none()
    firm_criado = firm is None
    if firm is None:
        firm = Firm(
            nome=config.firm_nome,
            meta_operacional=META_OPERACIONAL,
            limiar_confianca_parser=LIMIAR_CONFIANCA_PARSER,
            piso_economia_anual=PISO_ECONOMIA_ANUAL,
            cpp_das_integra_fs12=CPP_DAS_INTEGRA_FS12,
            tolerancia_ouro_pct=TOLERANCIA_OURO_PCT,
        )
        session.add(firm)
        await session.flush()

    user = (
        await session.execute(
            select(User).where(func.lower(User.email) == config.user_email.lower())
        )
    ).scalar_one_or_none()
    user_criado = user is None
    if user is None:
        session.add(
            User(
                firm_id=firm.id,
                email=config.user_email,
                senha_hash=hash_password(config.user_senha),
                nome=config.user_nome,
            )
        )
    await session.commit()
    return SeedResultado(
        firm_criado=firm_criado, user_criado=user_criado, faixas_inseridas=faixas_inseridas
    )


def _estado(criado: bool) -> str:
    return "criado" if criado else "já existia"


async def _main() -> None:
    config = SeedConfig.from_env()
    # Seed usa a role dona: caminho explícito fora do RLS (migração 0004).
    async with get_owner_sessionmaker()() as session:
        resultado = await seed(session, config)
    await get_owner_engine().dispose()
    sys.stdout.write(
        f"Escritório: {_estado(resultado.firm_criado)} · "
        f"Usuário: {_estado(resultado.user_criado)} · "
        f"Faixas do Simples inseridas: {resultado.faixas_inseridas}\n"
    )


if __name__ == "__main__":
    asyncio.run(_main())
