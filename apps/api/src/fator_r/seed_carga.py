"""Seed de carga (T-304): escritório separado com 200 empresas x 24 meses.

Uso: python -m fator_r.seed_carga  (role dona; nunca mexe no escritório padrão)
"""

import asyncio
import os
import sys
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.core.competencia import somar_meses
from fator_r.core.db import get_owner_engine, get_owner_sessionmaker
from fator_r.core.security import hash_password
from fator_r.repositories.orm import Company, Firm, MonthlyMovement, User

NOME_ESCRITORIO_CARGA = "Escritório Carga (perf)"


def _cnpj(indice: int) -> str:
    base = f"{90000000 + indice:08d}0001"

    def digito(numeros: str, pesos: list[int]) -> str:
        resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
        return "0" if resto < 2 else str(11 - resto)

    dv1 = digito(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    dv2 = digito(base + dv1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return base + dv1 + dv2


async def gerar_carga(
    session: AsyncSession, empresas: int = 200, meses: int = 24, ultimo_mes: date | None = None
) -> uuid.UUID:
    existente = (
        await session.execute(select(Firm).where(Firm.nome == NOME_ESCRITORIO_CARGA))
    ).scalar_one_or_none()
    if existente is not None:
        return existente.id
    firm = Firm(
        nome=NOME_ESCRITORIO_CARGA,
        meta_operacional=Decimal("0.30"),
        limiar_confianca_parser=Decimal("0.40"),
        piso_economia_anual=Decimal("6000"),
        cpp_das_integra_fs12=True,
        tolerancia_ouro_pct=Decimal("0.01"),
    )
    session.add(firm)
    await session.flush()
    fim = ultimo_mes or somar_meses(date.today().replace(day=1), -1)  # noqa: DTZ011
    inicio = somar_meses(fim, -(meses - 1))
    company_rows = []
    movement_rows = []
    for i in range(empresas):
        company_id = uuid.uuid4()
        company_rows.append(
            {
                "id": company_id,
                "firm_id": firm.id,
                "nome": f"Empresa de carga {i:03d}",
                "cnpj": _cnpj(i),
                "sujeita_fator_r": True,
                "honorario_mensal": Decimal("300"),
                "pacote": "monitoramento",
            }
        )
        receita = Decimal(20000 + (i % 20) * 5000)
        # Distribui entre vermelho, amarelo e verde.
        percentual = Decimal(["0.20", "0.29", "0.32"][i % 3])
        for k in range(meses):
            movement_rows.append(
                {
                    "firm_id": firm.id,
                    "company_id": company_id,
                    "competencia": somar_meses(inicio, k),
                    "receita_bruta": receita,
                    "pro_labore": (receita * percentual).quantize(Decimal("0.01")),
                    "origem": "manual",
                }
            )
    await session.execute(insert(Company), company_rows)
    await session.execute(insert(MonthlyMovement), movement_rows)
    await session.commit()
    return firm.id


EMAIL_USUARIO_CARGA = "carga@escritorio-carga.com.br"


async def _main() -> None:
    async with get_owner_sessionmaker()() as session:
        firm_id = await gerar_carga(session)
        senha = os.environ.get("SEED_CARGA_PASSWORD")
        existe = (
            await session.execute(select(User).where(User.email == EMAIL_USUARIO_CARGA))
        ).scalar_one_or_none()
        if senha and existe is None:
            session.add(
                User(
                    firm_id=firm_id,
                    email=EMAIL_USUARIO_CARGA,
                    senha_hash=hash_password(senha),
                    nome="Usuário de carga",
                )
            )
            await session.commit()
    await get_owner_engine().dispose()
    sys.stdout.write(f"Escritório de carga pronto: {firm_id}\n")


if __name__ == "__main__":
    asyncio.run(_main())
