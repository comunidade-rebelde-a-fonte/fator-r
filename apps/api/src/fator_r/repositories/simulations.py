import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.repositories.orm import Simulation


async def listar(
    session: AsyncSession, firm_id: uuid.UUID, company_id: uuid.UUID, limit: int = 10
) -> list[Simulation]:
    rows = await session.execute(
        select(Simulation)
        .where(Simulation.firm_id == firm_id, Simulation.company_id == company_id)
        .order_by(Simulation.criado_em.desc())
        .limit(limit)
    )
    return list(rows.scalars())


async def obter(
    session: AsyncSession, firm_id: uuid.UUID, simulation_id: uuid.UUID
) -> Simulation | None:
    return (
        await session.execute(
            select(Simulation).where(Simulation.firm_id == firm_id, Simulation.id == simulation_id)
        )
    ).scalar_one_or_none()
